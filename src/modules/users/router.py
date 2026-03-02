from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])

# Şu anda users router'ı boş kalacak çünkü login/register fonksiyonlarını auth'a taşıdık.
# İleride /users/me, /users/{id} gibi endpointler buraya eklenecektir.
