from fastapi import FastAPI

from benchmarks.common.models import UserIn, UserOut

app = FastAPI()


@app.post('/users', response_model=UserOut)
async def create_user(user: UserIn) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, tags=user.tags)


@app.get('/health')
async def health() -> str:
    return 'ok'
