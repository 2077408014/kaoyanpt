from typing import Optional, Union
from datetime import timedelta, datetime
from sqlalchemy.orm import Session
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..models.user import User
from ..models.password_reset import PasswordResetCode
from ..models.email_verification import EmailVerificationCode
from ..schemas.auth import UserCreate, UserLogin, TokenResponse
from ..core.security import verify_password, get_password_hash, create_access_token
from ..core.config import settings

class AuthService:
    def register(self, db: Session, user_data: UserCreate) -> User:
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        if existing_user:
            raise ValueError("用户名或邮箱已存在")
        
        if not getattr(user_data, 'code', None):
            raise ValueError("请先获取邮箱验证码")
        
        self.verify_email_code(db, user_data.email, user_data.code)
        
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password=hashed_password
        )
        db.add(new_user)
        db.flush()

        db.query(EmailVerificationCode).filter(
            EmailVerificationCode.email == user_data.email
        ).update({"used": True})

        db.commit()
        db.refresh(new_user)
        return new_user

    def login(self, db: Session, login_data: UserLogin) -> TokenResponse:
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user or not verify_password(login_data.password, user.password):
            raise ValueError("邮箱或密码错误")
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id, "type": "access"},
            expires_delta=access_token_expires
        )
        refresh_token = create_access_token(
            data={"sub": user.email, "user_id": user.id, "type": "refresh"},
            expires_delta=timedelta(days=7)
        )
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    def _generate_code(self) -> str:
        return ''.join(random.choices(string.digits, k=6))

    def send_password_reset_code(self, db: Session, email: str) -> bool:
        user = self.get_user_by_email(db, email)
        if not user:
            raise ValueError("该邮箱未注册")

        now = datetime.now()

        recent_code = db.query(PasswordResetCode).filter(
            PasswordResetCode.user_id == user.id,
            PasswordResetCode.created_at >= now - timedelta(minutes=1)
        ).first()
        if recent_code:
            raise ValueError("请求过于频繁，请稍后再试")

        db.query(PasswordResetCode).filter(
            PasswordResetCode.user_id == user.id,
            PasswordResetCode.used == False  # noqa: E712
        ).update({"used": True})

        code = self._generate_code()
        expires_at = now + timedelta(minutes=15)

        new_code = PasswordResetCode(
            user_id=user.id,
            code=code,
            expires_at=expires_at,
            used=False
        )
        db.add(new_code)
        db.flush()

        self._send_email(email, code, "考研复习平台 - 密码重置验证码")
        db.commit()
        return True

    def _send_email(self, to_email: str, code: str, subject: str):
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            raise ValueError("SMTP服务未配置，请联系管理员")

        try:
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
            msg['To'] = to_email
            msg['Subject'] = subject

            body = f"""尊敬的用户：

您的验证码是：

{code}

验证码有效期为15分钟，请及时使用。

如非本人操作，请忽略此邮件。

考研复习平台团队"""

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL or settings.SMTP_USER, to_email, msg.as_string())
        except Exception as e:
            print(f"Failed to send email: {e}")
            raise ValueError(f"邮件发送失败: {str(e)}")

    def verify_reset_code(self, db: Session, email: str, code: str) -> Optional[User]:
        user = self.get_user_by_email(db, email)
        if not user:
            return None

        reset_code = db.query(PasswordResetCode).filter(
            PasswordResetCode.user_id == user.id,
            PasswordResetCode.code == code,
            PasswordResetCode.used == False,  # noqa: E712
            PasswordResetCode.expires_at > datetime.now()
        ).first()

        if not reset_code:
            return None

        return user

    def reset_password(self, db: Session, email: str, code: str, new_password: str) -> bool:
        user = self.verify_reset_code(db, email, code)
        if not user:
            raise ValueError("验证码无效或已过期")

        if verify_password(new_password, user.password):
            raise ValueError("新密码不能与旧密码相同")

        hashed_password = get_password_hash(new_password)
        user.password = hashed_password
        db.commit()

        db.query(PasswordResetCode).filter(
            PasswordResetCode.user_id == user.id
        ).update({"used": True})
        db.commit()

        return True

    def send_email_verification_code(self, db: Session, email: str) -> bool:
        existing_user = self.get_user_by_email(db, email)
        if existing_user:
            raise ValueError("该邮箱已注册")

        now = datetime.now()

        recent_code = db.query(EmailVerificationCode).filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.created_at >= now - timedelta(minutes=1)
        ).first()
        if recent_code:
            raise ValueError("请求过于频繁，请稍后再试")

        db.query(EmailVerificationCode).filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.used == False  # noqa: E712
        ).update({"used": True})

        code = self._generate_code()
        expires_at = now + timedelta(minutes=15)

        new_code = EmailVerificationCode(
            email=email,
            code=code,
            expires_at=expires_at,
            used=False
        )
        db.add(new_code)
        db.flush()

        self._send_email(email, code, "考研复习平台 - 注册验证码")
        db.commit()
        return True

    def verify_email_code(self, db: Session, email: str, code: str) -> bool:
        verification = db.query(EmailVerificationCode).filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.code == code,
            EmailVerificationCode.used == False,  # noqa: E712
            EmailVerificationCode.expires_at > datetime.now()
        ).first()

        if not verification:
            raise ValueError("验证码无效或已过期")

        return True


auth_service = AuthService()