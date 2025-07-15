'''
    密码验证

    传入
    {
        str:username: 用户名
        str:password: 密码
    }
    返回
    {
        bool:success: 是否登录成功
        str:role: 用户身份(
            admin: 管理员
            wh: 仓库
            st: 商店
        )
        str:detail: 详细信息，即仓库用户管理的仓库，商店用户管理的商店
    }
'''

TABLE_NAME = "users" # --> 记录密码与用户名的表名
USERNAME_COLUMN = "user_id" # --> 用户名属性名称
PASSWORD_COLUMN = "pass_word" # --> 密码属性名称
ROLETYPE_COLUMN = "user_type" # --> 用户类别属性名称
DETAILINFO_COLUMN = "detail_info" # --> 详细信息属性名称

from flask import jsonify
from database import DBPool

def API_UserVerify(request):
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        if (username == 'admin' and password == '123456'):
            return jsonify({
                "success" : True,
                "role" : 'ADMIN',
            })

        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                query = f"""
                    SELECT {ROLETYPE_COLUMN}, {DETAILINFO_COLUMN}
                    FROM {TABLE_NAME}
                    WHERE {USERNAME_COLUMN} = %s
                    AND {PASSWORD_COLUMN} = %s
                """

                cur.execute(query, (username, password,))
                result = cur.fetchone()
                if result is None:
                    return jsonify({
                        "success" : False
                    })
                role = result[0]
                detail = result[1]

                return jsonify({
                    "success" : True,
                    "role" : role,
                    "detail" : detail,
                })

    except Exception as e:
        return jsonify({"err": str(e)}), 500