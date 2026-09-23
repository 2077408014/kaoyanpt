from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import SessionLocal


def _admin_password_hash() -> str:
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash("123456")


def seed_default_user(db: Session) -> None:
    count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
    if count and count > 0:
        return
    db.execute(
        text(
            "INSERT INTO users (username, email, password, daily_word_count) "
            "VALUES ('admin', 'admin@kaoyan.com', :password, 20)"
        ),
        {"password": _admin_password_hash()},
    )
    db.commit()


SAMPLE_WORDS = [
    ("abandon", "/əˈbændən/", "v. 放弃，抛弃", "He decided to abandon the project.", 1, 95, "高频词"),
    ("ability", "/əˈbɪləti/", "n. 能力，才能", "She has the ability to learn quickly.", 1, 88, "考纲词"),
    ("absolute", "/ˈæbsəluːt/", "adj. 绝对的，完全的", "This is an absolute truth.", 2, 75, "考纲词"),
    ("absorb", "/əbˈsɔːrb/", "v. 吸收；吸引", "Plants absorb carbon dioxide.", 2, 82, "高频词"),
    ("abstract", "/ˈæbstrækt/", "adj. 抽象的 n. 摘要", "Beauty is an abstract concept.", 3, 70, "考纲词"),
    ("academy", "/əˈkædəmi/", "n. 学院，研究院", "He graduated from the military academy.", 2, 60, "考纲词"),
    ("accelerate", "/əkˈseləreɪt/", "v. 加速，促进", "The car began to accelerate.", 2, 55, "考纲词"),
    ("access", "/ˈækses/", "n. 通道；使用权 v. 访问", "Students have access to the library.", 1, 90, "高频词"),
    ("accomplish", "/əˈkɒmplɪʃ/", "v. 完成，实现", "She accomplished her goal.", 2, 65, "考纲词"),
    ("accumulate", "/əˈkjuːmjəleɪt/", "v. 积累，积聚", "He accumulated a lot of experience.", 2, 58, "考纲词"),
    ("accurate", "/ˈækjərət/", "adj. 准确的，精确的", "The data must be accurate.", 2, 72, "考纲词"),
    ("achieve", "/əˈtʃiːv/", "v. 实现，达到", "You can achieve anything if you try.", 1, 92, "高频词"),
    ("acknowledge", "/əkˈnɒlɪdʒ/", "v. 承认；感谢", "He acknowledged his mistake.", 3, 50, "考纲词"),
    ("acquire", "/əˈkwaɪər/", "v. 获得，习得", "She acquired new skills.", 2, 68, "考纲词"),
    ("adapt", "/əˈdæpt/", "v. 适应，改编", "Animals adapt to their environment.", 2, 76, "考纲词"),
    ("adequate", "/ˈædɪkwət/", "adj. 足够的，适当的", "We have adequate resources.", 3, 52, "考纲词"),
    ("adjust", "/əˈdʒʌst/", "v. 调整，适应", "You need to adjust your plan.", 2, 74, "考纲词"),
    ("administrate", "/ədˈmɪnɪstreɪt/", "v. 管理，行政", "He administrates the department.", 3, 40, "考纲词"),
    ("admire", "/ədˈmaɪər/", "v. 钦佩，羡慕", "I admire your courage.", 2, 62, "考纲词"),
    ("admit", "/ədˈmɪt/", "v. 承认；准许进入", "He admitted his fault.", 1, 85, "高频词"),
    ("adopt", "/əˈdɒpt/", "v. 采用；收养", "They adopted a new policy.", 2, 66, "考纲词"),
    ("advance", "/ədˈvɑːns/", "v. 前进；推进 n. 进步", "Science advances rapidly.", 1, 80, "高频词"),
    ("advantage", "/ədˈvɑːntɪdʒ/", "n. 优势，有利条件", "He has an advantage over others.", 1, 86, "高频词"),
    ("adventure", "/ədˈventʃər/", "n. 冒险，奇遇", "Life is an adventure.", 2, 56, "考纲词"),
    ("advertise", "/ˈædvətaɪz/", "v. 做广告，宣传", "They advertise their products on TV.", 2, 54, "考纲词"),
    ("advise", "/ədˈvaɪz/", "v. 建议，劝告", "I advise you to study hard.", 1, 84, "高频词"),
    ("affect", "/əˈfekt/", "v. 影响，作用", "The weather affects my mood.", 1, 88, "高频词"),
    ("afford", "/əˈfɔːd/", "v. 负担得起", "I can't afford this car.", 2, 70, "考纲词"),
    ("aggressive", "/əˈɡresɪv/", "adj. 侵略的；积极的", "He is aggressive in business.", 3, 48, "考纲词"),
    ("agriculture", "/ˈæɡrɪkʌltʃər/", "n. 农业", "Agriculture is important for food.", 2, 50, "考纲词"),
]


def seed_words(db: Session) -> None:
    count = db.execute(text("SELECT COUNT(*) FROM words")).scalar()
    if count and count > 0:
        return
    for word in SAMPLE_WORDS:
        db.execute(
            text(
                "INSERT INTO words (word, phonetic, meaning, example_sentence, difficulty, frequency, exam_requirement) "
                "VALUES (:word, :phonetic, :meaning, :example, :diff, :freq, :req)"
            ),
            {
                "word": word[0],
                "phonetic": word[1],
                "meaning": word[2],
                "example": word[3],
                "diff": word[4],
                "freq": word[5],
                "req": word[6],
            },
        )
    db.commit()


def run_seed() -> None:
    with SessionLocal() as db:
        seed_default_user(db)
        seed_words(db)