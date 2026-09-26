"""多角色/班级体系接口与权限隔离集成测试。

独立 FastAPI 应用 + 内存 SQLite + TestClient，不触碰真实数据库。
运行方式：python3 backend/tests/test_organization_api.py
"""
import os
import sys
import traceback
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
import app.models  # noqa: 注册全部模型
from app.api import admin, teacher, institution, classes, auth
from app.models.user import User
from app.models.mistake import Mistake
from app.models.study_stat import UserStudyStat
from app.models.supervision import StudySupervisionRecord
from app.models.organization import (
    ROLE_TEACHER, ROLE_INSTITUTION_ADMIN, ROLE_SUPER_ADMIN,
)
from app.services.organization_service import organization_service as svc

# ---------- 测试应用与内存库（StaticPool 保证跨线程共享同一连接） ----------
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(teacher.router)
app.include_router(institution.router)
app.include_router(classes.router)
app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


def headers(uid: int, email: str) -> dict:
    token = create_access_token(
        data={"sub": email, "user_id": uid, "type": "access"}
    )
    return {"Authorization": f"Bearer {token}"}


# ---------- 基线数据 ----------
db = TestingSessionLocal()

admin_user = User(username="root", email="root@e.com", password="x", role=ROLE_SUPER_ADMIN)
iadmin = User(username="iadm", email="iadm@e.com", password="x",
              role=ROLE_INSTITUTION_ADMIN)
db.add_all([admin_user, iadmin])
db.commit()

inst_a = svc.create_institution(db, "甲机构")
inst_b = svc.create_institution(db, "乙机构")
# 机构管理者归属甲机构
iadmin.institution_id = inst_a.id
db.commit()

class_a = svc.create_class(db, inst_a.id, "甲一班")
class_b = svc.create_class(db, inst_b.id, "乙一班")

t_a = svc.create_staff_user(db, "teachA", "ta@e.com", "123456", ROLE_TEACHER, inst_a.id)
t_b = svc.create_staff_user(db, "teachB", "tb@e.com", "123456", ROLE_TEACHER, inst_b.id)
svc.assign_teacher(db, class_a.id, t_a.id)
svc.assign_teacher(db, class_b.id, t_b.id)

s1 = User(username="stu1", email="s1@e.com", password="x")
s2 = User(username="stu2", email="s2@e.com", password="x")
db.add_all([s1, s2])
db.commit()
db.refresh(s1); db.refresh(s2)

# s1 的学习数据（在入班前就存在）
db.add_all([
    Mistake(user_id=s1.id, subject="数学", knowledge_point="极限", error_type="概念错误",
            difficulty="中等", mastery_level="生疏", question_text="题1", answer="a"),
    Mistake(user_id=s1.id, subject="数学", knowledge_point="导数", error_type="计算错误",
            difficulty="简单", mastery_level="掌握", question_text="题2", answer="b"),
    Mistake(user_id=s1.id, subject="英语", knowledge_point="阅读", error_type="审题错误",
            difficulty="困难", mastery_level="熟悉", question_text="题3", answer="c"),
    UserStudyStat(user_id=s1.id, study_date=date.today(), total_time=600,
                  words_studied=15, mistakes_added=3, questions_completed=4),
    StudySupervisionRecord(user_id=s1.id, session_id="ss", status="distracted",
                           confidence=1.0, face_count=2),
])
db.commit()

# s2 加入乙机构班级（直接写成员关系）
svc.join_class(db, s2, class_b.join_code)

H_ADMIN = headers(admin_user.id, admin_user.email)
H_TA = headers(t_a.id, t_a.email)
H_TB = headers(t_b.id, t_b.email)
H_IADM = headers(iadmin.id, iadmin.email)
H_S1 = headers(s1.id, s1.email)


# ---------- 测试用例 ----------
def test_admin_endpoints_require_super_admin():
    assert client.get("/api/admin/institutions", headers=H_S1).status_code == 403
    r = client.get("/api/admin/institutions", headers=H_ADMIN)
    assert r.status_code == 200
    names = {x["name"] for x in r.json()}
    assert {"甲机构", "乙机构"} <= names


def test_admin_create_org_class_teacher_and_duplicate():
    r = client.post("/api/admin/institutions", json={"name": "丙机构"}, headers=H_ADMIN)
    assert r.status_code == 200
    inst_c_id = r.json()["id"]
    # 重名
    assert client.post("/api/admin/institutions", json={"name": "丙机构"},
                       headers=H_ADMIN).status_code == 400

    # 超管不再能管理班级：/api/admin/classes 已移除
    assert client.post("/api/admin/classes",
                       json={"name": "丙一班", "institution_id": inst_c_id},
                       headers=H_ADMIN).status_code == 404

    # 超管为丙机构创建机构管理者，由机构管理者建班
    r = client.post("/api/admin/users", json={
        "username": "iadmC", "email": "ic@e.com", "password": "123456",
        "role": "institution_admin", "institution_id": inst_c_id,
    }, headers=H_ADMIN)
    assert r.status_code == 200
    ic_id = r.json()["id"]
    h_ic = headers(ic_id, "ic@e.com")

    # 超管调机构写接口也被拒绝（403）
    assert client.post("/api/institution/classes",
                       json={"name": "丙一班", "institution_id": inst_c_id},
                       headers=H_ADMIN).status_code == 403

    r = client.post("/api/institution/classes",
                    json={"name": "丙一班"}, headers=h_ic)
    assert r.status_code == 200
    code = r.json()["join_code"]
    assert len(code) == 6 and code == code.upper()

    r = client.post("/api/admin/users", json={
        "username": "teachC", "email": "tc@e.com", "password": "123456",
        "role": "teacher", "institution_id": inst_c_id,
    }, headers=H_ADMIN)
    assert r.status_code == 200
    tc_id = r.json()["id"]

    # 非法角色被 schema 拒绝（422）
    r = client.post("/api/admin/users", json={
        "username": "bad", "email": "bad@e.com", "password": "123456",
        "role": "super_admin", "institution_id": inst_c_id,
    }, headers=H_ADMIN)
    assert r.status_code == 422

    # 分配教师（机构管理者操作）
    cclass = svc.list_classes(db, inst_c_id)[0]
    r = client.post(f"/api/institution/classes/{cclass.id}/teachers",
                    json={"teacher_id": tc_id}, headers=h_ic)
    assert r.status_code == 200


def test_student_join_flow():
    # 错误码
    r = client.post("/api/classes/join", json={"code": "ZZZZZZ"}, headers=H_S1)
    assert r.status_code == 400
    # 小写码等价
    r = client.post("/api/classes/join", json={"code": class_a.join_code.lower()},
                    headers=H_S1)
    assert r.status_code == 200
    assert r.json()["name"] == "甲一班"
    # 重复入班幂等
    r2 = client.post("/api/classes/join", json={"code": class_a.join_code}, headers=H_S1)
    assert r2.status_code == 200
    # 我的班级
    mine = client.get("/api/classes/my", headers=H_S1).json()
    assert {c["id"] for c in mine} == {class_a.id}
    # 双重角色：教师也可以学生身份入班（随后清理，保持后续用例不变）
    assert client.post("/api/classes/join", json={"code": class_a.join_code},
                       headers=H_TA).status_code == 200
    from app.models.organization import ClassStudent
    db.query(ClassStudent).filter(
        ClassStudent.class_id == class_a.id, ClassStudent.student_id == t_a.id
    ).delete()
    db.commit()


def test_teacher_class_scope():
    r = client.get("/api/teacher/classes", headers=H_TA)
    assert r.status_code == 200
    assert {c["id"] for c in r.json()} == {class_a.id}

    # 学生不能访问教师端
    assert client.get("/api/teacher/classes", headers=H_S1).status_code == 403

    # tA 看自己班学生：200 且包含 s1
    r = client.get(f"/api/teacher/classes/{class_a.id}/students", headers=H_TA)
    assert r.status_code == 200
    ids = {x["id"] for x in r.json()}
    assert ids == {s1.id}

    # tA 看 tB 带的班 → 403；tB 看 A 班 → 403
    assert client.get(f"/api/teacher/classes/{class_b.id}/students",
                      headers=H_TA).status_code == 403
    assert client.get(f"/api/teacher/classes/{class_a.id}/students",
                      headers=H_TB).status_code == 403


def test_student_overview_mistakes_and_stats():
    r = client.get(f"/api/teacher/students/{s1.id}/overview", headers=H_TA)
    assert r.status_code == 200
    data = r.json()
    assert data["study_time_7d"] == 10           # 600 秒 → 10 分钟
    assert data["words_7d"] == 15
    assert data["questions_7d"] == 4
    assert data["total_mistakes"] == 3
    assert data["mastered_mistakes"] == 1
    assert data["supervision_abnormal"] == 1
    assert len(data["daily"]) == 7
    # 今日（序列最后一天）五维数据齐全
    today = data["daily"][-1]
    assert today["study_time"] == 10
    assert today["words"] == 15
    assert today["questions"] == 4
    assert today["mistakes"] == 3
    assert today["abnormal"] == 1
    # 其余 6 天无数据补零
    assert all(d["study_time"] == 0 for d in data["daily"][:-1])

    # 错题列表
    r = client.get(f"/api/teacher/students/{s1.id}/mistakes", headers=H_TA)
    assert r.status_code == 200 and len(r.json()) == 3
    # 科目过滤
    r = client.get(f"/api/teacher/students/{s1.id}/mistakes?subject=数学", headers=H_TA)
    assert len(r.json()) == 2
    # 错题详情
    mid = client.get(f"/api/teacher/students/{s1.id}/mistakes", headers=H_TA).json()[0]["id"]
    assert client.get(f"/api/teacher/students/{s1.id}/mistakes/{mid}",
                      headers=H_TA).status_code == 200

    # tB 不能看 s1（不在其授权集合）
    assert client.get(f"/api/teacher/students/{s1.id}/overview",
                      headers=H_TB).status_code == 403


def test_institution_admin_scope():
    # 甲机构管理者只能看到甲机构班级
    r = client.get("/api/institution/classes", headers=H_IADM)
    assert r.status_code == 200
    inst_ids = {c["institution_id"] for c in r.json()}
    assert inst_ids == {inst_a.id}

    # 看 B 班学生 → 403
    assert client.get(f"/api/institution/classes/{class_b.id}/students",
                      headers=H_IADM).status_code == 403
    # 看本班学生 200
    assert client.get(f"/api/institution/classes/{class_a.id}/students",
                      headers=H_IADM).status_code == 200
    # 看 s1 overview / 错题
    assert client.get(f"/api/institution/students/{s1.id}/overview",
                      headers=H_IADM).status_code == 200

    # 学生不能访问机构端
    assert client.get("/api/institution/classes", headers=H_S1).status_code == 403

    # 超管必须指定 institution_id
    assert client.get("/api/institution/classes", headers=H_ADMIN).status_code == 400
    r = client.get(f"/api/institution/classes?institution_id={inst_b.id}", headers=H_ADMIN)
    assert r.status_code == 200
    assert {c["id"] for c in r.json()} == {class_b.id}


def test_remove_student_permissions_and_data_retained():
    # tB 无权移出 A 班学生
    r = client.delete(f"/api/teacher/classes/{class_a.id}/students/{s1.id}", headers=H_TB)
    assert r.status_code == 403

    # tA 移出
    r = client.delete(f"/api/teacher/classes/{class_a.id}/students/{s1.id}", headers=H_TA)
    assert r.status_code == 200
    ids = {x["id"] for x in client.get(
        f"/api/teacher/classes/{class_a.id}/students", headers=H_TA).json()}
    assert ids == set()

    # 学习数据仍在
    assert db.query(Mistake).filter(Mistake.user_id == s1.id).count() == 3

    # 可凭码重新加入
    r = client.post("/api/classes/join", json={"code": class_a.join_code}, headers=H_S1)
    assert r.status_code == 200
    ids = {x["id"] for x in client.get(
        f"/api/teacher/classes/{class_a.id}/students", headers=H_TA).json()}
    assert ids == {s1.id}


def test_class_summary_aggregates():
    r = client.get("/api/institution/classes", headers=H_IADM)
    a = next(c for c in r.json() if c["id"] == class_a.id)
    assert a["student_count"] == 1
    assert a["avg_study_time_7d"] == 10.0
    assert a["avg_words_7d"] == 15.0
    assert a["avg_questions_7d"] == 4.0
    assert a["avg_mistakes"] == 3.0
    assert a["total_mistakes"] == 3
    assert a["supervision_abnormal"] == 1


# ---------- 二期：入班码策略 / 改密 / 成员管理 / 机构写操作 / 公告 / 作业 / 双重角色 ----------

def test_reset_join_code_and_expiry_and_uses():
    # 由机构管理者建班：1 次上限 + 明天过期
    tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
    r = client.post("/api/institution/classes", json={
        "name": "策略班", "code_expires_at": tomorrow, "code_max_uses": 1,
    }, headers=H_IADM)
    assert r.status_code == 200
    cls_id = r.json()["id"]
    old_code = r.json()["join_code"]
    assert r.json()["code_max_uses"] == 1

    # 游离学生 s3 用掉唯一一次
    s3 = User(username="stu3", email="s3@e.com", password="x")
    db.add(s3); db.commit(); db.refresh(s3)
    h_s3 = headers(s3.id, s3.email)
    assert client.post("/api/classes/join", json={"code": old_code},
                       headers=h_s3).status_code == 200
    # 第二次达到上限
    r = client.post("/api/classes/join", json={"code": old_code}, headers=H_S1)
    assert r.status_code == 400 and "次数" in r.json()["detail"]
    # s1 幂等场景不适用（未加入）—— 清掉 s3 后再验过期：重置码并设为已过期
    r = client.patch(f"/api/institution/classes/{cls_id}", json={
        "code_max_uses": None,
        "code_expires_at": (datetime.now() - timedelta(hours=1)).isoformat(),
    }, headers=H_IADM)
    assert r.status_code == 200 and r.json()["code_max_uses"] is None
    r = client.post("/api/classes/join", json={"code": old_code}, headers=H_S1)
    assert r.status_code == 400 and "过期" in r.json()["detail"]

    # 重置入班码并清除时效，旧码失效、新码可用
    r = client.post(f"/api/institution/classes/{cls_id}/reset-code", headers=H_IADM)
    assert r.status_code == 200
    new_code = r.json()["join_code"]
    assert new_code != old_code
    assert client.post("/api/classes/join", json={"code": old_code},
                       headers=H_S1).status_code == 400
    r = client.patch(f"/api/institution/classes/{cls_id}",
                     json={"code_expires_at": None}, headers=H_IADM)
    assert r.status_code == 200
    assert client.post("/api/classes/join", json={"code": new_code},
                       headers=H_S1).status_code == 200


def test_force_change_password_on_created_staff():
    # 管理员创建的教师带 must_change_password 标记（/me 可见）
    r = client.get("/api/auth/me", headers=H_TA)
    assert r.status_code == 200 and r.json()["must_change_password"] is True
    # 原密码错误 → 400
    r = client.post("/api/auth/change-password",
                    json={"old_password": "wrong", "new_password": "newpass1"},
                    headers=H_TA)
    assert r.status_code == 400
    # 正常修改
    r = client.post("/api/auth/change-password",
                    json={"old_password": "123456", "new_password": "newpass1"},
                    headers=H_TA)
    assert r.status_code == 200
    assert client.get("/api/auth/me", headers=H_TA).json()["must_change_password"] is False


def test_manual_add_suspend_restore():
    # tB 无权往 A 班加人
    r = client.post(f"/api/teacher/classes/{class_a.id}/students/add",
                    json={"email": "s3@e.com"}, headers=H_TB)
    assert r.status_code == 403
    # 未注册邮箱 → 400
    r = client.post(f"/api/teacher/classes/{class_a.id}/students/add",
                    json={"email": "nobody@e.com"}, headers=H_TA)
    assert r.status_code == 400
    # s2 已属乙机构 → 400
    r = client.post(f"/api/teacher/classes/{class_a.id}/students/add",
                    json={"email": "s2@e.com"}, headers=H_TA)
    assert r.status_code == 400 and "其他机构" in r.json()["detail"]
    # tA 把 s3（当前在"策略班"，该班也属甲机构）加进甲一班
    r = client.post(f"/api/teacher/classes/{class_a.id}/students/add",
                    json={"email": "s3@e.com"}, headers=H_TA)
    assert r.status_code == 200
    roster = {x["id"] for x in client.get(
        f"/api/teacher/classes/{class_a.id}/students", headers=H_TA).json()}
    assert s3_id_lookup("s3@e.com") in roster

    # 暂停 s3：学生内容接口 403、凭码加入 403
    sid = s3_id_lookup("s3@e.com")
    assert client.post(f"/api/teacher/classes/{class_a.id}/students/{sid}/suspend",
                       headers=H_TA).status_code == 200
    h_s3 = headers(sid, "s3@e.com")
    assert client.get(f"/api/classes/{class_a.id}/announcements",
                      headers=h_s3).status_code == 403
    # 暂停期间看板聚合不计入
    r = client.get("/api/institution/classes", headers=H_IADM)
    a = next(c for c in r.json() if c["id"] == class_a.id)
    assert a["student_count"] == 1  # 只剩 s1
    # 恢复后正常
    assert client.post(f"/api/teacher/classes/{class_a.id}/students/{sid}/restore",
                       headers=H_TA).status_code == 200
    assert client.get(f"/api/classes/{class_a.id}/announcements",
                      headers=h_s3).status_code == 200


def s3_id_lookup(email: str) -> int:
    return db.query(User).filter(User.email == email).first().id


def test_institution_admin_writes_scoped():
    # 机构管理者在本机构建班（无需 institution_id）
    r = client.post("/api/institution/classes", json={"name": "甲机构自建班"}, headers=H_IADM)
    assert r.status_code == 200
    own_class_id = r.json()["id"]
    assert r.json()["institution_id"] == inst_a.id

    # 建教师账号并分配
    r = client.post("/api/institution/teachers", json={
        "username": "teachX", "email": "tx@e.com", "password": "123456",
    }, headers=H_IADM)
    assert r.status_code == 200
    tx_id = r.json()["id"]
    assert r.json()["institution_id"] == inst_a.id
    r = client.post(f"/api/institution/classes/{own_class_id}/teachers",
                    json={"teacher_id": tx_id}, headers=H_IADM)
    assert r.status_code == 200

    # 教师列表只含本机构
    ids = {u["id"] for u in client.get("/api/institution/teachers", headers=H_IADM).json()}
    assert tx_id in ids and t_b.id not in ids

    # 重置本机构班入班码
    assert client.post(f"/api/institution/classes/{own_class_id}/reset-code",
                       headers=H_IADM).status_code == 200
    # 越权改乙机构班 → 403
    assert client.patch(f"/api/institution/classes/{class_b.id}",
                        json={"name": "黑掉乙班"}, headers=H_IADM).status_code == 403
    assert client.post(f"/api/institution/classes/{class_b.id}/reset-code",
                       headers=H_IADM).status_code == 403
    # 超管无班级管理权限 → 403
    assert client.post("/api/institution/classes", json={"name": "超管班"},
                       headers=H_ADMIN).status_code == 403
    assert client.patch(f"/api/institution/classes/{own_class_id}",
                        json={"name": "超管改名"}, headers=H_ADMIN).status_code == 403
    assert client.post(f"/api/institution/classes/{own_class_id}/reset-code",
                       headers=H_ADMIN).status_code == 403
    assert client.post("/api/institution/teachers", json={
        "username": "teachSA", "email": "tsa@e.com", "password": "123456",
    }, headers=H_ADMIN).status_code == 403


def test_institution_teacher_update_delete():
    # 新建一名待操作的本机构教师
    r = client.post("/api/institution/teachers", json={
        "username": "teachEdit", "email": "te@e.com", "password": "123456",
    }, headers=H_IADM)
    assert r.status_code == 200
    tid = r.json()["id"]
    # 分配到甲机构自建班（上个用例所建），用于验证删除时任教关系一并解除
    own_class_id = next(
        c["id"] for c in client.get("/api/institution/classes", headers=H_IADM).json()
        if c["name"] == "甲机构自建班"
    )
    assert client.post(f"/api/institution/classes/{own_class_id}/teachers",
                       json={"teacher_id": tid}, headers=H_IADM).status_code == 200

    # 编辑用户名/邮箱，不传密码
    r = client.put(f"/api/institution/teachers/{tid}", json={
        "username": "teachEdit2", "email": "te2@e.com",
    }, headers=H_IADM)
    assert r.status_code == 200
    assert r.json()["username"] == "teachEdit2"
    assert r.json()["email"] == "te2@e.com"

    # 重置密码后需再次强制改密
    r = client.put(f"/api/institution/teachers/{tid}",
                   json={"password": "654321"}, headers=H_IADM)
    assert r.status_code == 200 and r.json()["must_change_password"] is True

    # 重复用户名 → 400
    r = client.put(f"/api/institution/teachers/{tid}",
                   json={"username": "teachA"}, headers=H_IADM)
    assert r.status_code == 400

    # 越权操作乙机构教师 t_b → 403
    assert client.put(f"/api/institution/teachers/{t_b.id}",
                      json={"username": "hacked"}, headers=H_IADM).status_code == 403
    assert client.delete(f"/api/institution/teachers/{t_b.id}",
                         headers=H_IADM).status_code == 403
    # 超管无教师写权限 → 403
    assert client.put(f"/api/institution/teachers/{tid}",
                      json={"username": "hackadmin"}, headers=H_ADMIN).status_code == 403
    assert client.delete(f"/api/institution/teachers/{tid}",
                         headers=H_ADMIN).status_code == 403

    # 删除本机构教师
    assert client.delete(f"/api/institution/teachers/{tid}",
                         headers=H_IADM).status_code == 200
    # 再删 → 404
    assert client.delete(f"/api/institution/teachers/{tid}",
                         headers=H_IADM).status_code == 404
    # 任教关系已一并解除
    assigned = client.get(f"/api/institution/classes/{own_class_id}/teachers",
                          headers=H_IADM).json()
    assert all(t["id"] != tid for t in assigned)


def test_announcement_crud_and_read_scope():
    # tA 发公告
    r = client.post(f"/api/teacher/classes/{class_a.id}/announcements", json={
        "title": "国庆安排", "content": "放假三天",
    }, headers=H_TA)
    assert r.status_code == 200
    ann_id = r.json()["id"]
    assert r.json()["author_name"] == "teachA"

    # 学生可见
    r = client.get(f"/api/classes/{class_a.id}/announcements", headers=H_S1)
    assert r.status_code == 200 and r.json()[0]["title"] == "国庆安排"
    # 外班学生 s2 不可见
    assert client.get(f"/api/classes/{class_a.id}/announcements",
                      headers=headers(s2.id, s2.email)).status_code == 403
    # tB 不能在 A 班发公告
    assert client.post(f"/api/teacher/classes/{class_a.id}/announcements",
                       json={"title": "x", "content": "y"},
                       headers=H_TB).status_code == 403
    # 编辑 / 删除
    assert client.put(f"/api/teacher/announcements/{ann_id}",
                      json={"content": "放假两天"}, headers=H_TA).status_code == 200
    assert client.delete(f"/api/teacher/announcements/{ann_id}",
                         headers=H_TA).status_code == 200
    assert client.get(f"/api/classes/{class_a.id}/announcements",
                      headers=H_S1).json() == []


def test_assignment_lifecycle_submit_grade_resubmit():
    # 已过截止时间的作业
    r = client.post(f"/api/teacher/classes/{class_a.id}/assignments", json={
        "title": "迟到作业", "content": "答完",
        "due_at": (datetime.now() - timedelta(hours=1)).isoformat(),
    }, headers=H_TA)
    assert r.status_code == 200
    late_id = r.json()["id"]
    assert client.post(f"/api/classes/assignments/{late_id}/submissions",
                       json={"content": "我的答案"}, headers=H_S1).status_code == 400

    # 正常作业
    r = client.post(f"/api/teacher/classes/{class_a.id}/assignments", json={
        "title": "第一次作业", "content": "论述题",
        "due_at": (datetime.now() + timedelta(days=7)).isoformat(),
    }, headers=H_TA)
    assert r.status_code == 200
    asm_id = r.json()["id"]

    # 学生提交
    r = client.post(f"/api/classes/assignments/{asm_id}/submissions",
                    json={"content": "学生答案"}, headers=H_S1)
    assert r.status_code == 200
    # 教师看到提交统计
    r = client.get(f"/api/teacher/assignments/{asm_id}", headers=H_TA)
    assert r.json()["submission_count"] == 1 and r.json()["graded_count"] == 0
    # 打分
    r = client.post(f"/api/teacher/assignments/{asm_id}/grade", json={
        "student_id": s1.id, "score": 90, "feedback": "不错",
    }, headers=H_TA)
    assert r.status_code == 200
    # 学生端看到分数
    r = client.get(f"/api/classes/assignments/{asm_id}", headers=H_S1)
    assert r.json()["my_submission"]["score"] == 90
    # 重新提交后评分清空
    r = client.post(f"/api/classes/assignments/{asm_id}/submissions",
                    json={"content": "修改后的答案"}, headers=H_S1)
    assert r.status_code == 200 and r.json()["score"] is None
    # 外班教师无权评分
    assert client.post(f"/api/teacher/assignments/{asm_id}/grade", json={
        "student_id": s1.id, "score": 60,
    }, headers=H_TB).status_code == 403


def test_assignment_images():
    # 上传图片（教师身份）
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    r = client.post("/api/teacher/assignments/upload-image",
                    files={"file": ("t.png", png, "image/png")}, headers=H_TA)
    assert r.status_code == 200
    img_path = r.json()["image_path"]
    assert img_path.startswith("assignments/")
    # 非教师禁止上传
    assert client.post("/api/teacher/assignments/upload-image",
                       files={"file": ("t.png", png, "image/png")},
                       headers=H_S1).status_code == 403
    # 非法类型
    assert client.post("/api/teacher/assignments/upload-image",
                       files={"file": ("t.txt", b"hi", "text/plain")},
                       headers=H_TA).status_code == 400

    # 创建作业带图片
    r = client.post(f"/api/teacher/classes/{class_a.id}/assignments", json={
        "title": "带图作业", "content": "见图", "images": [img_path],
    }, headers=H_TA)
    assert r.status_code == 200 and r.json()["images"] == [img_path]
    asm_id = r.json()["id"]

    # 教师列表 / 学生详情都能看到图片
    r = client.get(f"/api/teacher/classes/{class_a.id}/assignments", headers=H_TA)
    assert any(a["id"] == asm_id and a["images"] == [img_path] for a in r.json())
    r = client.get(f"/api/classes/assignments/{asm_id}", headers=H_S1)
    assert r.json()["images"] == [img_path]

    # 更新图片（不传 images 时保持不变）
    r = client.put(f"/api/teacher/assignments/{asm_id}",
                   json={"content": "改内容"}, headers=H_TA)
    assert r.json()["images"] == [img_path]
    r = client.put(f"/api/teacher/assignments/{asm_id}",
                   json={"images": []}, headers=H_TA)
    assert r.status_code == 200 and r.json()["images"] == []

    # 图片已落盘（线上由 /uploads 静态挂载提供访问，测试应用未挂载）
    from app.core.config import UPLOAD_PATH
    assert (UPLOAD_PATH / img_path).exists()
    (UPLOAD_PATH / img_path).unlink()  # 清理测试产物


def test_dual_role_staff_as_student():
    # tA（甲机构教师）凭乙班码以学生身份加入
    r = client.post("/api/classes/join", json={"code": class_b.join_code}, headers=H_TA)
    assert r.status_code == 200 and r.json()["status"] == "active"
    mine = {c["id"] for c in client.get("/api/classes/my", headers=H_TA).json()}
    assert class_b.id in mine
    # 能以成员身份看乙班公告（空列表 200）
    assert client.get(f"/api/classes/{class_b.id}/announcements",
                      headers=H_TA).status_code == 200
    # 教师工作台权限不受影响
    assert client.get("/api/teacher/classes", headers=H_TA).status_code == 200


CASES = [
    test_admin_endpoints_require_super_admin,
    test_admin_create_org_class_teacher_and_duplicate,
    test_student_join_flow,
    test_teacher_class_scope,
    test_student_overview_mistakes_and_stats,
    test_institution_admin_scope,
    test_remove_student_permissions_and_data_retained,
    test_class_summary_aggregates,
    test_reset_join_code_and_expiry_and_uses,
    test_force_change_password_on_created_staff,
    test_manual_add_suspend_restore,
    test_institution_admin_writes_scoped,
    test_institution_teacher_update_delete,
    test_announcement_crud_and_read_scope,
    test_assignment_lifecycle_submit_grade_resubmit,
    test_assignment_images,
    test_dual_role_staff_as_student,
]

if __name__ == "__main__":
    failed = 0
    for fn in CASES:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:
            failed += 1
            traceback.print_exc()
            print(f"FAIL {fn.__name__}")
    if failed:
        raise SystemExit(f"{failed} 个测试失败")
    print("PASS: 全部多角色/班级接口测试通过")
