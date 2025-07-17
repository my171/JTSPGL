# 集团商品智能管理系统

## Prerequisite

Before the deployment, you have to make sure that you have met the following requests:

- Node.js installed
- Python installed
- Have openai, and qwen API

## Deployment

### Database Deployment

- Adopt openGauss 5.0.0 or newer version

- Import the companylink.sql file as the database

- Modify the ./back/config.py file by replacing the connection address with the local machine's IP address, and update the database user, database name, and password with the actual credentials

### Run the program

Change directory to the parent folder of the README.md

Install necessary denpendency packages

```shell
install -r requirements.txt
```

Before proceeding, you have to replace parameters in './back/agentrag1.py', specifically API parameter, with your own one.

Run back end script

```shell
python ./back/app.py
```

Run front end code

```shell
cd ./front/JTSPGL-web
npm install
npm run dev
```