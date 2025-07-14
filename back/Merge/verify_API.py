from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from database import DBPool

import sys
import locale

def UserVerify(request):
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        with DBPool.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT roletype
                    FROM user_list
                    WHERE username = %s
                    AND pword = %s
                """

                cur.execute(query, (username, password,))
                result = cur.fetchone()
                if result is None:
                    return jsonify({
                        "success" : False
                    })
                role = result[0]

                return jsonify({
                    "success" : True,
                    "role" : role,
                })

    except Exception as e:
        print(str(e))
        return jsonify({"err": str(e)}), 500