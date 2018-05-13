from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from wtforms.validators import DataRequired
from passlib.hash import sha256_crypt
from functools import wraps
import requests
from bs4 import BeautifulSoup
app = Flask(__name__)

mysql=MySQL(app)#completed la connection between flask and mysql
app.secret_key="fblog"
app.config["MYSQL_HOST"]="localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="fblog"
app.config["MYSQL_CURSORCLASS"]="DictCursor"

#user enter decorater
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in"  in session:
            return f(*args, **kwargs)
        else:
            flash("please log in to view this page","danger")
            return  redirect(url_for("login"))
    return decorated_function


class LoginForm(Form):
    username=StringField("User name")
    password=PasswordField("Parola",validators=[DataRequired("pls enter password")])
#how to register


class RegisterForm(Form):
    name = StringField('name', validators=[validators.length(min=4,max=25)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email Address', [validators.Email(message="check your email")])
    password = PasswordField('New Password: ',[
        validators.DataRequired(message="pls write a pswd"),
        validators.EqualTo(fieldname='confirm', message='Password doesn"t match')
    ])
    confirm = PasswordField('Confirm  password')


@app.route('/register', methods=["GET","POST"])
def register():
    form= RegisterForm(request.form)#if there is a request post ot get ,we place
    if request.method== "POST" and form.validate():
        name=form.name.data
        username=form.username.data
        email=form.email.data
        password= sha256_crypt.encrypt(form.password.data)

        cursor=mysql.connection.cursor()
        sorgu = 'INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s)'
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()
        cursor.close()

        flash("Succesfully registered","success")# we'll see it in the next page index.html

        return redirect(url_for("login"))
    else:
        return render_template("register.html",form=form)#to show form on html page


@app.route('/')
#jinja template is used
def index():
    return render_template("index.html")

@app.route('/abaut')
def abaut():
    return render_template("abaut.html")

def getGitReposinfos():
    cursor = mysql.connection.cursor()
    base_url = "https://api.github.com/repositories?q=flask"
    user_url = "https://api.github.com/users/"
    repos_url = "https://github.com"
    fRepos = requests.get(base_url)

    repoInfo = fRepos.json()
    i = 0
    while i < 10:
        for repo in repoInfo:
            i += 1
            name = repo["owner"]["login"]
            uInfos = requests.get(user_url + name)
            uInfo = uInfos.json()
            getRepo = requests.get(uInfo["repos_url"])
            control = "Select * from pinfo where login = %s"
            result = cursor.execute(control, (uInfo["login"],))
            if result == 0:
                for getname in getRepo.json():
                    rName = getname["full_name"]
                    read = requests.get(repos_url + "/" + rName + "/blob/master/README.md")
                    soup = BeautifulSoup(read.content, "lxml")
                    content = soup.find_all("div", attrs={"id": "readme"})
                    for readme in content:
                        query = 'INSERT INTO pinfo(login,avatar,followers,following,blog,public_repos,repos_url,created_at,rName,readme) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
                        cursor.execute(query,
                                       (uInfo["login"], uInfo["avatar_url"], uInfo["followers"], uInfo["following"],
                                        uInfo["blog"],
                                        uInfo["public_repos"], uInfo["repos_url"], uInfo["created_at"], rName,
                                        readme.text))
                    mysql.connection.commit()

    cursor.close()


@app.route("/tools",methods=["GET","POST"])
def addtool():
    if request.method == "GET":
         cursor = mysql.connection.cursor()
         query = "Select *from pinfo"
         result = cursor.execute(query)
         if result > 0:
             fInfos = cursor.fetchall()
             return render_template("tools.html", fInfos=fInfos)

    else:

        return render_template("index.html")

@app.route("/detail/<string:login>")
def repodetail(login):
    cursor = mysql.connection.cursor()
    query = "Select *from pinfo"
    result = cursor.execute(query)
    if result > 0:
        fInfos = cursor.fetchone()
        return render_template("repodetail.html", fInfos=fInfos)
    # cursor = mysql.connection.cursor()
    # query = "SELECT *FROM articles"
    #
    # result = cursor.execute(query)
    #
    # if result > 0:
    #     article = cursor.fetchall()
    #
    #     return render_template("tools.html", articles=article)
    #
    # else:
    #     return render_template("index.html")
    #return render_template("tools.html")


#login app
@app.route('/login',methods=["GET","POST"])
def login():
    form=LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data
        cursor = mysql.connection.cursor()

        uquery="SELECT *FROM users WHERE username = %s"
        result = cursor.execute(uquery,(username,))
        if result >0:
            data=cursor.fetchone()
            real_password=data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Login succeeded","success")
                session["logged_in"]= True#check the session to continue procesess
                session["username"] = username


                return redirect(url_for("index"))
            else:
                flash("Check your password","danger")
                return redirect(url_for("login"))



        else:
            flash("Couldn't find this user!","danger")
            redirect(url_for("login"))

    return render_template("login.html",form=form)

#@app.route('/article/<string:id>')
#def detail(id):

#    return "article" +id

#user login form
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

#detail page
@app.route("/article/<string:id>")
def detail(id):
    cursor=mysql.connection.cursor()
    query ="Select * From articles where id = %s"

    result= cursor.execute(query,(id,))

    if result> 0:
        article=cursor.fetchone()
        return render_template("article.html",article=article)

    else:
        return render_template("article.html")



@app.route("/index")
def articles():
    cursor=mysql.connection.cursor()
    query="SELECT *FROM articles"

    result =cursor.execute(query)

    if result>0:
        article=cursor.fetchall()

        return render_template("index.html",articles=article)

    else:
        return render_template("index.html")


@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()

    query = "Select * From articles where author = %s"

    result = cursor.execute(query, (session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles=articles)
    else:
        return render_template("dashboard.html")

#add article
@app.route("/addarticle",methods=["GET","POST"])
def addarcile():
    form=ArticleForm(request.form)
    if request.method =="POST" and form.validate():
        title=form.title.data
        content=form.content.data
        cursor =mysql.connection.cursor()

        query="INSERT INTO articles(title,author,content) VALUES(%s,%s,%s)"

        cursor.execute(query,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Article added successfully","success")

        return redirect(url_for("dashboard"))


    return render_template("addarticle.html",form=form)

#delete article
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()

    sorgu = "Select * from articles where author = %s and id = %s"

    result = cursor.execute(sorgu,(session["username"],id))

    if result > 0:
        sorgu2 = "Delete from articles where id = %s"

        cursor.execute(sorgu2, (id,))

        mysql.connection.commit()

        return redirect(url_for("dashboard"))
    else:
        flash("dont permission", "danger")
        return redirect(url_for("index"))


#update article
@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required

def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()

        sorgu = "Select * from articles where id = %s and author = %s"
        result = cursor.execute(sorgu, (id, session["username"]))

        if result == 0:
            flash("You dont have permission", "danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form=form)

    else:
        # POST REQUEST
        form = ArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "Update articles Set title = %s,content = %s where id = %s "

        cursor = mysql.connection.cursor()

        cursor.execute(sorgu2, (newTitle, newContent, id))

        mysql.connection.commit()

        flash("Article updated", "success")

        return redirect(url_for("dashboard"))









#create a article
class ArticleForm(Form):

    title=StringField("title",validators=[validators.length(min=5,max=120)])
    content=TextAreaField("Content",validators=[validators.length(min=10)])

#search url
@app.route("/search",methods=["GET","POST"])
def search():
    if request.method =="GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()

        query = "Select * from articles where title like '%" + keyword + "%'"

        result = cursor.execute(query)

        if result == 0:
            #flash("not match any article ...","")
            return redirect(url_for("index"))
        else:
            articles = cursor.fetchall()

            return render_template("index.html", articles=articles)


if __name__ == '__main__':
    app.run(debug=True)
