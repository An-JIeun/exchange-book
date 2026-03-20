from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    nickname: str
    password: str


class UserLogin(BaseModel):
    nickname: str
    password: str


class UserSignup(BaseModel):
    nickname: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    is_admin: bool = False
    current_book_id: int | None = None
    current_page: int | None = None
    next_book_id: int | None = None


class UserDashboardUpdate(BaseModel):
    current_book_id: int | None = None
    current_page: int | None = None
    next_book_id: int | None = None


class BookCreate(BaseModel):
    title: str
    author: str
    cover_url: str | None = None


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    cover_url: str | None = None


class UnderlineCreate(BaseModel):
    book_id: int
    user_id: int
    page: int
    content: str
    is_public: bool = True
    initial_comment: str | None = None


class UnderlineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    user_id: int
    page: int
    content: str
    is_public: bool


class CommentCreate(BaseModel):
    underline_id: int
    user_id: int
    content: str


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    underline_id: int
    user_id: int
    content: str


class DashboardRead(BaseModel):
    user: UserRead
    current_book: BookRead | None = None
    next_book: BookRead | None = None
