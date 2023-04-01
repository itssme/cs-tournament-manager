from endpoints.db_endpoints import get
from endpoints.db_endpoints import post
from endpoints.db_endpoints import delete


def set_api_routes(app, cache, server_manger):
    get.set_api_routes(app, cache, server_manger)
    post.set_api_routes(app, cache, server_manger)
    delete.set_api_routes(app, cache, server_manger)
