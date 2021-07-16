#!/usr/bin/env python3
# --------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2021 Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
# --------------------------------------------------------------------------------------
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type

from aiohttp import ClientResponseError
from fastapi.encoders import jsonable_encoder
from pydantic import AnyHttpUrl
from ramodels.mo import Employee
from ramodels.mo import OrganisationUnit
from ramodels.mo._shared import MOBase
from ramodels.mo.details import Address
from ramodels.mo.details import Engagement
from ramodels.mo.details import EngagementAssociation
from ramodels.mo.details import Manager
from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential

from raclients.modelclientbase import ModelClientBase


class ModelClient(ModelClientBase):
    __mo_path_map = {
        OrganisationUnit: "/service/ou/create",
        Employee: "/service/e/create",
        Engagement: "/service/details/create",
        EngagementAssociation: "/service/details/create",
        Manager: "/service/details/create",
        Address: "/service/details/create",
    }

    def __init__(
        self,
        base_url: AnyHttpUrl = AnyHttpUrl(
            "http://localhost:5000", scheme="http", host="localhost"
        ),
        force: bool = False,
        *args: Any,
        **kwargs: Optional[Any],
    ):
        super().__init__(base_url, *args, **kwargs)  # type: ignore
        self.force = int(force)

    def _get_healthcheck_tuples(self) -> List[Tuple[str, str]]:
        return [("/version/", "mo_version")]

    def _get_path_map(self) -> Dict[MOBase, str]:
        return self.__mo_path_map

    @retry(wait=wait_exponential(multiplier=2, min=1), stop=stop_after_attempt(7))
    async def _post_single_to_backend(
        self, current_type: Type[MOBase], obj: MOBase
    ) -> Any:
        session = await self._verify_session()
        post_url = (
            f"{self._base_url}{self.__mo_path_map[current_type]}?force={self.force}"
        )

        async with session.post(post_url, json=jsonable_encoder(obj)) as response:
            resp = await response.json()
            try:
                response.raise_for_status()
            except ClientResponseError as client_err:
                if "description" in resp:
                    client_err.message = resp["description"]
                raise client_err
            return resp

    async def load_mo_objs(
        self, objs: Iterable[MOBase], disable_progressbar: bool = False
    ) -> List[Any]:
        """
        lazy init client session to ensure created within async context
        :param objs:
        :param disable_progressbar:
        :return:
        """
        return await self._submit_payloads(
            objs, disable_progressbar=disable_progressbar
        )
