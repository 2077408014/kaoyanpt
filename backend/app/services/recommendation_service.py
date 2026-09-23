from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
from ..models.recommendation import Recommendation, UserWeakPoint
from ..models.mistake import Mistake
from ..schemas.recommendation import RecommendationCreate, RecommendationComplete
from ..agents.orchestrator import recommendation_orchestrator
from ..agents.specialized import register_all_agents
from ..services.agent_log_service import agent_log_service
from ..utils.latex_utils import normalize_latex
from .llm_service import llm_service


register_all_agents()


class RecommendationService:
    def analyze_weak_points(self, db: Session, user_id: int) -> list:
        mistakes = db.query(Mistake).filter(Mistake.user_id == user_id).all()

        weak_points = {}
        for mistake in mistakes:
            key = (mistake.subject, mistake.knowledge_point)
            if key not in weak_points:
                weak_points[key] = 0
            weak_points[key] += 1

        result = []
        for (subject, knowledge_point), count in weak_points.items():
            existing = db.query(UserWeakPoint).filter(
                UserWeakPoint.user_id == user_id,
                UserWeakPoint.subject == subject,
                UserWeakPoint.knowledge_point == knowledge_point
            ).first()

            weak_level = min(5, count)

            if existing:
                existing.weak_level = weak_level
                existing.mistake_count = count
                existing.updated_at = datetime.now()
            else:
                new_weak_point = UserWeakPoint(
                    user_id=user_id,
                    subject=subject,
                    knowledge_point=knowledge_point,
                    weak_level=weak_level,
                    mistake_count=count
                )
                db.add(new_weak_point)

        db.commit()

        weak_points_list = db.query(UserWeakPoint).filter(UserWeakPoint.user_id == user_id).all()
        for wp in weak_points_list:
            result.append({
                "subject": wp.subject,
                "knowledge_point": wp.knowledge_point,
                "weak_level": wp.weak_level,
                "mistake_count": wp.mistake_count,
                "updated_at": wp.updated_at
            })

        return result

    async def generate_recommendations(self, db: Session, user_id: int, count: int = 5, subject: str = None, progress_callback=None) -> list:
        from ..services.ai_service import ai_service
        from ..agents.base import agent_registry

        # 检查智能出题智能体是否启用
        if not agent_registry.is_agent_enabled('recommendation_agent'):
            raise ValueError("智能出题功能已被停用。请前往首页，在「智能体状态」中开启「智能出题助手」。")

        user_config = ai_service._get_user_ai_config(db, user_id)

        if not user_config["api_key"]:
            raise ValueError("无法生成推荐题目：请先在AI配置页面设置API Key")

        weak_points = self.analyze_weak_points(db, user_id)

        filtered_weak_points = weak_points
        if subject:
            filtered_weak_points = [wp for wp in weak_points if wp["subject"] == subject]

        if not filtered_weak_points:
            if subject:
                raise ValueError(f"无法生成推荐题目：科目「{subject}」暂无薄弱知识点，请先添加该科目的错题")
            else:
                raise ValueError("无法生成推荐题目：暂无薄弱知识点，请先添加错题")

        total_steps = min(count, len(filtered_weak_points))
        if progress_callback:
            progress_callback(0, f"开始生成，共需 {total_steps} 道题...")

        recommendations = []

        try:
            ai_recommendations = await self._generate_ai_recommendations(db, user_id, filtered_weak_points, count, subject, progress_callback=progress_callback)
            recommendations.extend(ai_recommendations)
        except ValueError as ve:
            raise ve
        except Exception as e:
            print(f"生成AI推荐题目失败: {e}")
            raise ValueError(f"AI生成题目失败: {str(e)}")

        if not recommendations:
            if subject:
                raise ValueError(f"无法生成推荐题目：科目「{subject}」暂无薄弱知识点，请先添加该科目的错题")
            else:
                raise ValueError("无法生成推荐题目：暂无薄弱知识点，请先添加错题")

        db_recommendations = []

        for rec in recommendations:
            question_text = rec.get("question_text", "").strip()
            answer = rec.get("answer", "").strip()

            if not question_text or not answer:
                print(f"跳过无效推荐（空题目或答案）: question='{question_text[:50]}...', answer='{answer[:50]}...'")
                continue

            existing = db.query(Recommendation).filter(
                Recommendation.user_id == user_id,
                Recommendation.question_text == question_text,
                Recommendation.completed == False
            ).first()

            if not existing:
                new_rec = Recommendation(
                    user_id=user_id,
                    subject=rec.get("agent_domain", rec.get("subject", "未知")),
                    knowledge_point=rec.get("knowledge_point", "")[:100] if rec.get("knowledge_point") else "",
                    difficulty=rec.get("difficulty", "中等"),
                    question_text=question_text,
                    answer=answer,
                    analysis=rec.get("analysis", "").strip(),
                    source=rec.get("source", "AI生成"),
                    result=None,
                    completed=False
                )
                db.add(new_rec)
                db_recommendations.append(new_rec)

        db.commit()

        return [self._to_dict(rec) for rec in db_recommendations]

    async def _generate_ai_recommendations(self, db: Session, user_id: int, weak_points: list, count: int, subject: str = None, progress_callback=None) -> list:
        from ..services.rag_service import rag_service
        from ..services.ai_service import ai_service

        recommendations = []

        filtered_weak_points = weak_points
        if subject:
            filtered_weak_points = [wp for wp in weak_points if wp["subject"] == subject]

        filtered_weak_points = [wp for wp in filtered_weak_points if wp.get("knowledge_point") and wp["knowledge_point"].strip() not in ("", "未分类")]

        if not filtered_weak_points:
            if subject:
                raise ValueError(f"科目「{subject}」暂无明确薄弱知识点，请先添加该科目的错题")
            else:
                raise ValueError("暂无薄弱知识点，请先添加错题")

        user_config = ai_service._get_user_ai_config(db, user_id)

        subject_prompts = {
            "数学": "考研数学出题专家，精通高等数学、线性代数、概率论与数理统计",
            "英语": "考研英语出题专家，精通阅读理解、完形填空、翻译、写作等所有题型",
            "政治": "考研政治出题专家，精通马原、毛中特、史纲、思修、时政等所有政治科目",
            "专业课": "考研专业课出题专家"
        }

        schema_hint = '{"question_text": "题目内容", "answer": "答案内容", "analysis": "解析内容", "difficulty": "简单/中等/困难"}'

        try:
            total = min(count, len(filtered_weak_points))
            idx = 0
            for wp in filtered_weak_points[:count]:
                wp_subject = wp["subject"]
                knowledge_point = wp["knowledge_point"]

                if progress_callback:
                    progress_callback(int(idx / total * 80), f"正在生成第 {idx + 1}/{total} 道题（{knowledge_point}）...")

                idx += 1

                try:
                    search_query = f"{wp_subject} {knowledge_point} 考研题目"
                    rag_result = rag_service.chat(user_id, search_query, top_k=3, threshold=0.3, ai_config=user_config, subject=wp_subject)

                    context = ""
                    for chunk in rag_result.get("relevant_chunks", []):
                        chunk_subject = chunk['metadata'].get('subject', '未分类')
                        if chunk_subject != wp_subject and chunk_subject != "全部":
                            continue
                        context += f"【来源：{chunk['metadata'].get('filename', '未知文档')}】\n"
                        context += f"{chunk['content']}\n\n"
                except Exception:
                    context = ""

                expert_role = subject_prompts.get(wp_subject, f"考研{wp_subject}出题专家")
                subject_restriction = f"\n【绝对禁止】你绝对不能生成{wp_subject}以外的任何科目的题目。即使你看到参考内容是其他科目的，也必须只出{wp_subject}题。"
                math_formula_note = "\n2. 数学公式必须使用标准LaTeX格式（行内$...$，块级$$...$$）" if wp_subject == "数学" else ""

                system_prompt = f"你是一个专业的{expert_role}，擅长根据知识点生成高质量的考研练习题。你严格遵守科目边界，绝不跨科目出题。"

                user_prompt = f"""请生成一道关于【{wp_subject} - {knowledge_point}】的考研练习题。

知识库参考内容：
{context if context else "（暂无知识库内容，请根据你的专业知识出题）"}

要求：
1. 题目必须是严格的{wp_subject}科目题目，难度适中，符合考研真题水平
2. 绝对禁止生成{wp_subject}以外的任何科目题目（如数学、英语、政治等），即使参考内容涉及其他科目{subject_restriction}
3. 必须包含完整的题目、答案和解析，所有字段内容不能为空或空字符串
4. difficulty字段只能是"简单"、"中等"或"困难"三者之一
5. question_text至少10个字，answer至少2个字，analysis至少10个字
6. 数学公式必须使用标准LaTeX格式（行内$...$，块级$$...$$）

只输出JSON，不要任何其他文字！"""

                try:
                    parsed = llm_service.generate_json(
                        user_message=user_prompt,
                        ai_config=user_config,
                        system_prompt=system_prompt,
                        temperature=0.5,
                        max_tokens=1024,
                        max_retries=1,
                        schema_hint=schema_hint,
                    )

                    item = None
                    if isinstance(parsed, dict):
                        item = parsed
                    elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                        item = parsed[0]

                    if item and item.get("question_text", "").strip() and item.get("answer", "").strip():
                        recommendations.append({
                            "question_text": normalize_latex(item["question_text"].strip()),
                            "answer": normalize_latex(item["answer"].strip()),
                            "analysis": normalize_latex(item.get("analysis", "").strip()),
                            "difficulty": item.get("difficulty", "中等"),
                            "agent_domain": wp_subject,
                            "knowledge_point": knowledge_point,
                            "source": "AI+知识库" if context else "AI生成",
                            "confidence": 0.85
                        })
                        if progress_callback:
                            progress_callback(int(idx / total * 80), f"已生成 {len(recommendations)} 道题，继续生成中...")
                    else:
                        print(f"AI返回内容缺少必要字段或字段为空: {str(parsed)[:200]}...")
                except ValueError as ve:
                    print(f"生成题目失败（{wp_subject}-{knowledge_point}）: {ve}")
                    continue

                if len(recommendations) >= count:
                    break

            if progress_callback:
                progress_callback(90, f"题目生成完成，正在保存...")

        except ValueError as ve:
            raise ve
        except Exception as e:
            print(f"AI生成推荐题目失败: {e}")
            raise ValueError(f"AI生成题目失败：{str(e)}")

        if not recommendations:
            raise ValueError("AI未能生成有效题目，请检查AI配置或稍后重试")

        return recommendations

    def get_recommendations(self, db: Session, user_id: int, completed: bool = False, subject: str = None) -> list:
        query = db.query(Recommendation).filter(Recommendation.user_id == user_id)
        if completed is not None:
            query = query.filter(Recommendation.completed == completed)
        if subject:
            query = query.filter(Recommendation.subject == subject)

        recommendations = query.order_by(Recommendation.created_at.desc()).all()
        return [self._to_dict(rec) for rec in recommendations]

    def complete_recommendation(self, db: Session, user_id: int, rec_id: int, result: str) -> dict:
        rec = db.query(Recommendation).filter(
            Recommendation.id == rec_id,
            Recommendation.user_id == user_id
        ).first()

        if not rec:
            return None

        rec.completed = True
        rec.result = result
        rec.completion_time = datetime.now()
        db.commit()

        return self._to_dict(rec)

    def delete_recommendation(self, db: Session, user_id: int, rec_id: int) -> bool:
        """删除单条推荐记录（独立方法，不影响其他业务）。"""
        rec = db.query(Recommendation).filter(
            Recommendation.id == rec_id,
            Recommendation.user_id == user_id
        ).first()
        if not rec:
            return False
        db.delete(rec)
        db.commit()
        return True

    def get_recommendation_report(self, db: Session, user_id: int) -> dict:
        total = db.query(Recommendation).filter(Recommendation.user_id == user_id).count()
        completed = db.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.completed == True
        ).count()
        correct = db.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.completed == True,
            Recommendation.result == "正确"
        ).count()

        weak_points = db.query(UserWeakPoint).filter(UserWeakPoint.user_id == user_id).all()

        return {
            "total_recommendations": total,
            "completed_recommendations": completed,
            "correct_recommendations": correct,
            "accuracy_rate": round(correct / completed * 100, 2) if completed > 0 else 0,
            "weak_points": [
                {
                    "subject": wp.subject,
                    "knowledge_point": wp.knowledge_point,
                    "weak_level": wp.weak_level,
                    "mistake_count": wp.mistake_count
                }
                for wp in sorted(weak_points, key=lambda x: x.weak_level, reverse=True)
            ]
        }

    def get_agent_status(self) -> list:
        return recommendation_orchestrator.get_agent_status()

    def toggle_agent(self, agent_name: str, enabled: bool):
        recommendation_orchestrator.toggle_agent(agent_name, enabled)

    def _to_dict(self, rec: Recommendation) -> dict:
        return {
            "id": rec.id,
            "user_id": rec.user_id,
            "subject": rec.subject,
            "knowledge_point": rec.knowledge_point,
            "difficulty": rec.difficulty,
            "question_text": rec.question_text,
            "answer": rec.answer,
            "analysis": rec.analysis,
            "source": rec.source,
            "completed": rec.completed,
            "result": rec.result,
            "completion_time": rec.completion_time.isoformat() if rec.completion_time else None,
            "created_at": rec.created_at.isoformat() if rec.created_at else None
        }


recommendation_service = RecommendationService()