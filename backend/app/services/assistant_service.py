"""教师 / 机构管理者 AI 助手：构建真实数据上下文与系统提示词。

只做只读聚合与提示词拼装，不执行任何写操作。
"""
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.user import User
from ..models.organization import (
    Class, Assignment, AssignmentSubmission, ROLE_SUPER_ADMIN,
)
from .organization_service import organization_service as svc
from .stats_query_service import stats_query_service as stats


# ---------- 教师 ----------

def _class_assignment_brief(db: Session, class_id: int, limit: int = 5) -> list[dict]:
    asms = (
        db.query(Assignment)
        .filter(Assignment.class_id == class_id)
        .order_by(Assignment.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for a in asms:
        submitted = db.query(func.count(AssignmentSubmission.id)).filter(
            AssignmentSubmission.assignment_id == a.id
        ).scalar()
        graded = db.query(func.count(AssignmentSubmission.id)).filter(
            AssignmentSubmission.assignment_id == a.id,
            AssignmentSubmission.score.isnot(None),
        ).scalar()
        result.append({
            "title": a.title,
            "due_at": a.due_at.strftime("%Y-%m-%d %H:%M") if a.due_at else "无截止",
            "submitted": int(submitted or 0),
            "graded": int(graded or 0),
        })
    return result


def build_teacher_context(db: Session, user: User) -> str:
    classes = svc.list_teacher_classes(db, user)
    lines = [f"今天是 {date.today().isoformat()}。", f"该教师共任教 {len(classes)} 个班级。"]
    for cls in classes:
        members = stats.class_student_summaries(db, cls.id)
        active = [m for m in members if m["status"] == "active"]
        suspended = [m for m in members if m["status"] == "suspended"]
        lines.append(f"\n## 班级：{cls.name}（在读 {len(active)} 人，暂停 {len(suspended)} 人）")
        lines.append(
            "学生明细（学习分钟/单词/做题为近7天累计，错题与监督异常为累计值）："
        )
        for m in members:
            lines.append(
                f"- {m['username']}（{'暂停' if m['status'] == 'suspended' else '在读'}）："
                f"学习{m['study_time_7d']}分钟，单词{m['words_7d']}，"
                f"做题{m['questions_7d']}，错题{m['total_mistakes']}，"
                f"监督异常{m['supervision_abnormal']}次"
            )
        briefs = _class_assignment_brief(db, cls.id)
        if briefs:
            lines.append("最近作业（标题/截止时间/已提交/已批）：")
            for b in briefs:
                lines.append(
                    f"- 《{b['title']}》截止{b['due_at']}，"
                    f"已提交{b['submitted']}人，已批{b['graded']}人"
                )
    return "\n".join(lines)


TEACHER_SYSTEM_PROMPT = """你是 KaoYanPT 考研陪伴平台的**教师 AI 助手**。

你的职责：
1. 基于下方提供的真实班级数据，回答教师关于学生学习情况的问题，做对比、找问题、给建议。
2. 主动识别需要关注的学生：近7天学习时长极低、单词/做题为 0、错题积压多、监督异常频繁、作业未提交等。
3. 给出具体、可执行的教学建议（如何时提醒、提醒谁、作业怎么调整）。

要求：
- 只用提供的数据回答，**严禁编造**数据；数据里没有的信息明确说"暂无数据"。
- 数据口径：学习分钟/单词/做题为近7天累计；错题数、监督异常为累计值；暂停成员不计入教学干预。
- 回答简洁有条理，适当使用小标题和列表；中文回答。
- 你只能分析和建议，不能替教师执行任何操作（发公告、改作业等请到对应页面操作）。
- 需要用流程图、决策树等图示说明时，**必须**输出 mermaid 围栏代码块：三个反引号后紧跟 mermaid 并立即换行，首行声明 flowchart TD 或 flowchart LR，结尾三个反引号独占一行。节点 ID 只用英文字母和数字，节点文字简短并用英文双引号包裹，保证语法严格合法、可被 mermaid 直接渲染；不要用表格或竖线、箭头等字符手工拼流程图。

以下是该教师任教班级的实时数据：
{context}
"""


# ---------- 机构管理者 ----------

def build_institution_context(db: Session, user: User) -> Optional[str]:
    if user.role == ROLE_SUPER_ADMIN or not user.institution_id:
        return None
    inst = svc.get_institution(db, user.institution_id)
    classes = svc.list_institution_classes(db, user)
    teachers = svc.list_staff_users(db, role="teacher", institution_id=user.institution_id)

    lines = [
        f"今天是 {date.today().isoformat()}。",
        f"机构名称：{inst.name if inst else '未知'}。",
        f"机构下共 {len(classes)} 个班级、{len(teachers)} 名教师。",
    ]
    total_students = 0
    for cls in classes:
        agg = stats.class_summary(db, cls.id)
        total_students += agg["student_count"]
        lines.append(
            f"\n## 班级：{cls.name}\n"
            f"- 在读学生：{agg['student_count']} 人\n"
            f"- 近7天人均：学习{agg['avg_study_time_7d']}分钟、"
            f"单词{agg['avg_words_7d']}、做题{agg['avg_questions_7d']}\n"
            f"- 人均累计错题：{agg['avg_mistakes']}（全班累计 {agg['total_mistakes']}）\n"
            f"- 累计监督异常：{agg['supervision_abnormal']} 次"
        )
    lines.append(f"\n在读学生总数：{total_students} 人。")
    lines.append("教师名单：" + "、".join(t.username for t in teachers))
    return "\n".join(lines)


INSTITUTION_SYSTEM_PROMPT = """你是 KaoYanPT 考研陪伴平台的**机构管理者 AI 助手**。

你的职责：
1. 基于下方机构真实数据，分析各班级整体学习情况：哪个班投入高、哪个班需要关注、资源如何调配。
2. 帮助管理者做教师/班级管理决策，给出具体可执行的建议。
3. 当管理者要求**创建教师账号**且提供了用户名和邮箱时，输出一张创建确认卡片（系统会自动识别，不要在正文里编造密码）。
   - 信息不全时，先追问用户名和邮箱，不要臆造。
   - 管理者只说"创建账号"未说明角色时，默认创建教师账号。

要求：
- 只用提供的数据回答，**严禁编造**；没有的数据明确说"暂无数据"。
- 数据口径：学习/单词/做题为近7天人均；错题与监督异常为累计值。
- 回答简洁有条理，适当使用小标题和列表；中文回答。
- 除"创建教师账号（需管理者二次确认）"外，你不能执行任何写操作。
- 需要用流程图、决策树等图示说明时，**必须**输出 mermaid 围栏代码块：三个反引号后紧跟 mermaid 并立即换行，首行声明 flowchart TD 或 flowchart LR，结尾三个反引号独占一行。节点 ID 只用英文字母和数字，节点文字简短并用英文双引号包裹，保证语法严格合法、可被 mermaid 直接渲染；不要用表格或竖线、箭头等字符手工拼流程图。

以下是该机构的实时数据：
{context}
"""


# ---------- 意图识别（创建教师） ----------

INTENT_SYSTEM_PROMPT = """你是一个意图识别器。判断用户最新消息是否**明确要求创建/新建/添加一个教师账号**。

判定规则：
1. 仅当消息明确表达创建教师账号意图，**且同时包含用户名和邮箱**时，输出：
   {"action": "create_teacher", "args": {"username": "用户名", "email": "邮箱", "password": "6位数字密码"}}
2. 密码：用户消息里给了就用给出的（至少6位）；没给就生成一个随机6位数字密码。
3. 其他一切情况（数据分析、询问、闲聊、信息不全、创建班级/学生/管理者等其他对象）一律输出：
   {"action": null}

只输出 JSON，不要任何解释或 markdown 标记。"""
