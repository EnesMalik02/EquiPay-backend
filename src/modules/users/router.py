from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])

# İleride /users/{id} gibi endpointler buraya eklenecektir.
