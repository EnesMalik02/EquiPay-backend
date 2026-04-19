import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.ratelimit import rate_limit
from src.core.security import get_current_user
from src.modules.users.models import User
from src.modules.friendships.schemas import (
    FriendRequestCreate,
    FriendRequestRespond,
    FriendResponse,
    FriendRequestResponse,
    FriendUserInfo,
)
from src.modules.friendships import services

router = APIRouter(prefix="/friendships", tags=["Friendships"])


@router.post("", status_code=status.HTTP_201_CREATED, summary="Arkadaşlık isteği gönder", dependencies=[Depends(rate_limit("20/minute"))])
async def send_friend_request(
    data: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        friendship = await services.send_request(
            db,
            requester_id=current_user.id,
            addressee_email=str(data.email) if data.email else None,
            addressee_phone=data.phone,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return {"id": str(friendship.id), "status": friendship.status}


@router.get("", response_model=list[FriendResponse], summary="Arkadaş listesi", dependencies=[Depends(rate_limit("60/minute"))])
async def list_friends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    friendships = await services.get_friends(db, current_user.id)
    result = []
    for f in friendships:
        friend_user = f.addressee if f.requester_id == current_user.id else f.requester
        result.append(FriendResponse(
            friendship_id=f.id,
            user=FriendUserInfo(
                id=friend_user.id,
                email=friend_user.email,
                display_name=friend_user.display_name,
                avatar_url=friend_user.avatar_url,
                username=friend_user.username,
            ),
            created_at=f.created_at,
        ))
    return result


@router.get("/pending", response_model=list[FriendRequestResponse], summary="Gelen arkadaşlık istekleri", dependencies=[Depends(rate_limit("60/minute"))])
async def list_pending_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    friendships = await services.get_pending_requests(db, current_user.id)
    return [
        FriendRequestResponse(
            id=f.id,
            requester=FriendUserInfo(
                id=f.requester.id,
                email=f.requester.email,
                display_name=f.requester.display_name,
                avatar_url=f.requester.avatar_url,
                username=f.requester.username,
            ),
            created_at=f.created_at,
        )
        for f in friendships
    ]


@router.patch("/{friendship_id}", summary="Arkadaşlık isteğini yanıtla", dependencies=[Depends(rate_limit("20/minute"))])
async def respond_to_request(
    friendship_id: uuid.UUID,
    data: FriendRequestRespond,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.action not in {"accept", "reject"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="action 'accept' veya 'reject' olmalıdır.")

    friendship = await services.get_friendship_by_id(db, friendship_id)
    if not friendship:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arkadaşlık isteği bulunamadı.")

    if friendship.addressee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca alıcı yanıt verebilir.")

    if friendship.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu istek zaten yanıtlanmış.")

    if data.action == "accept":
        updated = await services.accept_request(db, friendship)
        return {"id": str(updated.id), "status": updated.status}
    else:
        await services.delete_friendship(db, friendship)
        return {"detail": "İstek reddedildi."}


@router.delete("/{friendship_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Arkadaşlıktan çık / İsteği sil", dependencies=[Depends(rate_limit("20/minute"))])
async def remove_friendship(
    friendship_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    friendship = await services.get_friendship_by_id(db, friendship_id)
    if not friendship:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arkadaşlık kaydı bulunamadı.")

    if current_user.id not in {friendship.requester_id, friendship.addressee_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu işlem için yetkiniz yok.")

    await services.delete_friendship(db, friendship)
