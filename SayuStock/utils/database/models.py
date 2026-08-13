"""SsBind watchlist model — JSON-backed via gsuid_core Bind shim (no SQLModel)."""
from __future__ import annotations

from typing import Optional, Type

from gsuid_core.utils.database.base_models import Bind, T_Bind
from gsuid_core.webconsole.mount_app import PageSchema, GsAdminModel, site

from ..utils import convert_list


class SsBind(Bind):
    __tablename__ = "ss_bind"

    @classmethod
    async def delete_uid(
        cls: Type[T_Bind],
        user_id: str,
        bot_id: str,
        uid: str,
        game_name: Optional[str] = None,
    ) -> int:
        result = await cls.get_uid_list_by_game(user_id, bot_id, game_name)
        if result is None:
            return -1

        result = convert_list(result)

        if uid not in result:
            return -1

        result.remove(uid)
        result = [i for i in result if i] if result else []
        new_uid = "_".join(result)

        if not new_uid:
            await cls.delete_row(user_id=user_id, bot_id=bot_id)
            return 0

        await cls.update_data(
            user_id,
            bot_id,
            **{cls.get_gameid_name(game_name): new_uid},
        )
        return 0


@site.register_admin
class SsPushAdmin(GsAdminModel):
    pk_name = "id"
    page_schema = PageSchema(label="股票自选管理", icon="fa fa-bullhorn")
    model = SsBind
