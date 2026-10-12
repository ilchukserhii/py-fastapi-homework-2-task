from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas import MovieListResponseSchema, MovieCreateSchema, MovieDetailResponseSchema, MovieUpdateSchema


router = APIRouter()


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20)
):
    skip = (page - 1) * per_page
    queryset = await db.execute(
        select(MovieModel).
        order_by(MovieModel.id.desc()).
        offset(skip).
        limit(per_page)
    )
    movies = queryset.scalars().all()

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")
    total_results = await db.execute(select(func.count(MovieModel.id)))
    total_items = total_results.scalar_one()
    total_pages = (total_items + per_page - 1) // per_page

    prev_page = (
        f"/theater/movies/?page={page - 1}&per_page={per_page}"
        if page > 1
        else None
    )

    next_page = (
        f"/theater/movies/?page={page + 1}&per_page={per_page}"
        if page < total_pages
        else None
    )

    return {
        "movies": movies,
        "prev_page": prev_page,
        "next_page": next_page,
        "total_pages": total_pages,
        "total_items": total_items,
    }


async def get_or_create_related(model, names: list[str], db: AsyncSession):
    objects = []

    for name in names:
        obj = await db.scalar(
            select(model).where(model.name == name)
        )

        if obj is None:
            obj = model(name=name)
            db.add(obj)

        objects.append(obj)

    return objects


@router.post(
    "/movies/",
    response_model=MovieDetailResponseSchema,
    status_code=201
)
async def create_film(movie: MovieCreateSchema, db: AsyncSession = Depends(get_db)):
    movie_data = movie.model_dump(
        exclude={"country", "genres", "actors", "languages"}
    )

    new_movie = MovieModel(**movie_data)
    country_obj = await db.scalar(
        select(CountryModel).where(CountryModel.code == movie.country)
    )

    if country_obj is None:
        country_obj = CountryModel(code=movie.country)
        db.add(country_obj)

    new_movie.country = country_obj
    db.add(new_movie)

    with db.no_autoflush:
        new_movie.actors = await get_or_create_related(
            ActorModel, movie.actors, db
        )

        new_movie.genres = await get_or_create_related(
            GenreModel, movie.genres, db
        )

        new_movie.languages = await get_or_create_related(
            LanguageModel, movie.languages, db
        )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()

        error_message = str(exc.orig)

        if (
            "unique_movie_constraint" in error_message
            or "UNIQUE constraint failed: movies.name, movies.date" in error_message
        ):
            raise HTTPException(
                status_code=409,
                detail=f"A movie with the name '{movie.name}' and release date '{movie.date}' already exists.",
            ) from exc

        raise

    await db.refresh(
        new_movie,
        attribute_names=["country", "genres", "actors", "languages"]
    )

    return new_movie


@router.get("/movies/{movie_id}/", response_model=MovieDetailResponseSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.execute(
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages)
        )
        .where(MovieModel.id == movie_id)
    )
    movie_result = movie.scalar_one_or_none()

    if not movie_result:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    return movie_result


@router.delete("/movies/{movie_id}/", status_code=204)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie_result = await db.get(MovieModel, movie_id)
    if movie_result is None:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    await db.delete(movie_result)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/movies/{movie_id}/")
async def update_movie(
    movie_id: int,
    movie: MovieUpdateSchema,
    db: AsyncSession = Depends(get_db),
):
    updated_data = movie.model_dump(exclude_unset=True)

    db_film = await db.get(MovieModel, movie_id)

    if db_film is None:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    for field, value in updated_data.items():
        setattr(db_film, field, value)

    await db.commit()

    return {"detail": "Movie updated successfully."}
