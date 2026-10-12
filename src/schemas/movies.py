import datetime

from datetime import date, timedelta
from database.models import MovieStatusEnum
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MovieBase(BaseModel):
    name: str = Field(max_length=255)
    date: datetime.date
    score: float = Field(ge=0, le=100)
    overview: str


class MovieListItemSchema(MovieBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    prev_page: str | None
    next_page: str | None
    total_pages: int
    total_items: int


class MovieCreateSchema(MovieBase):
    date: date

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: date) -> date:
        max_date = date.today() + timedelta(days=365)

        if value > max_date:
            raise ValueError("Date must not be more than one year in the future")

        return value

    status: MovieStatusEnum
    budget: float = Field(ge=0)
    revenue: float = Field(ge=0)
    country: str = Field(
        min_length=2,
        max_length=3,
        pattern=r"^[A-Z]{2,3}$"
    )
    genres: list[str]
    actors: list[str]
    languages: list[str]


class CountryResponseSchema(BaseModel):
    id: int
    code: str
    name: str | None

    model_config = ConfigDict(from_attributes=True)


class GenreResponseSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class ActorResponseSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class LanguageResponseSchema(BaseModel):
    id: int
    name: str


class MovieDetailResponseSchema(MovieBase):
    id: int
    status: MovieStatusEnum
    budget: float
    revenue: float
    country: CountryResponseSchema
    genres: list[GenreResponseSchema]
    actors: list[ActorResponseSchema]
    languages: list[LanguageResponseSchema]

    model_config = ConfigDict(from_attributes=True)


class MovieUpdateSchema(MovieBase):
    name: str | None = None
    date: datetime.date | None = None
    score: float | None = Field(default=None, ge=0, le=100)
    overview: str | None = None
    status: MovieStatusEnum | None = None
    budget: float | None = Field(default=None, ge=0)
    revenue: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(from_attributes=True)
