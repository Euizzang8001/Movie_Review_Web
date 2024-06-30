import psycopg2
from flask import Flask, render_template, request, url_for, redirect
from datetime import datetime #리뷰 작성 날짜 저장을 위해 해당 라이브러리를 import
app = Flask(__name__)
connect = psycopg2.connect("dbname=postgres user=postgres password=postgres")
cur = connect.cursor()  # create cursor


@app.route('/')
def login(): #로그인 및 회원가입을 해야하는 페이지를 가장 먼저 보여줌
    return render_template("login.html", error_message="")

@app.route('/register', methods=['get', 'post']) #회원가입 및 로그인을 하는 기능
def register():
    id = request.form["id"] #사용자가 입력한 아이디
    password = request.form["password"] #사용자가 입력한 비밀번호
    send = request.form["send"] #회원가입과 로그인 중 사용자가 어떤 기능을 원하는지 나타냄

    if send == 'sign up': #사용자가 회원가입을 원한다면
        cur.execute(f"SELECT id FROM users where id = '{id}';") #현재 db에 같은 아이디가 있는지 찾아보고
        result = cur.fetchall()
        if result == [] and len(id)>0 and len(password)>0: #같은 아이디로 된 user가 존재하지 않으면서 id와 비밀번호가 빈칸이 아니라면 회원가입 정보를 db에 저장
            cur.execute(f"INSERT INTO users VALUES('{id}','{password}', 'user');")
            connect.commit()
            return id + " " + password + " " + send + " " + "success" #회원가입이 성공적이라는 것을 보여줌
        else: #회원가입 가능 조건이 되지 않는다면
            if len(id)<0 or len(password)<0: #아이디와 비밀번호가 빈칸이라 회원가입이 안된다면 해당 오류를 사용자에 전달
                return render_template("login.html", error_message="아이디와 비밀번호는 빈칸일 수 없습니다.")
            #이미 같은 id가 있다면 해당 오류를 사용자에 전달
            return render_template("login.html", error_message="이미 가입되어 있는 id입니다.")

    elif send == 'sign in': #사용자가 로그인을 원한다면
        cur.execute(f"SELECT id, password FROM users WHERE id = '{id}' and password = '{password}';") #사용자의 id와 비밀번호를 db에서 찾아보고
        result = cur.fetchall()
        if result == []: #해당 비밀번호로 설정된 id가 없다면
            cur.execute(f"SELECT id FROM users WHERE id = '{id}';") #id는 db에 있는지 찾아보고
            exist_id = cur.fetchall()
            if exist_id == []: #id조차 없으면 회원가입이 아직 안된 id이므로 회원가입 요청 문구를 전달
                return render_template("login.html", error_message="가입되어 있지 않은 회원입니다. 가입부터 해주세요.")
            else: #id는 있다면 비밀번호가 틀렸다는 문구를 사용자에 전달
                return render_template("login.html", error_message="비밀번호가 틀립니다.")
        else: #해당 비밀번호로 된 아이디가 있다면, 로그인이 성공적이므로 main화면으로 이동
            return redirect(url_for('main', username=result[0][0], movie = 'main', review = 'main'))

@app.route('/main', methods=['get']) # 메인 화면
def main():
    username = request.args['username']
    movie = request.args['movie']
    review = request.args['review'] #username은 로그인한 유저의 id, movie와 review는 각각 정렬 방법을 저장한 변수로 각각 main으로 저장되어 있으면 정렬하지 않은 데이터를 그대로 사용
    #영화에 대한 정보들을 db에서 가져와 movies에 저장
    cur.execute("WITH avg_rating(id, value) as (select mid, avg(ratings) from reviews group by mid) select title, trunc(value, 1), director, genre, rel_date from movies natural left outer join avg_rating;")
    movies = cur.fetchall()
    #리뷰에 대한 정보들을 db에서 가져와 reviews에 저장(로그인한 사용자가 mute한 사용자는 나타나지 않음)
    cur.execute(f"select A.ratings, A.uid, B.title, A.review, to_char(A.rev_time, 'YYYY-MM-DD HH24:MI'), A.likes_count, A.mid FROM reviews as A, movies as B where A.mid = B.id and A.uid not in (select C.opid from ties as C where C.tie = 'mute' and C.id = '{username}');")
    reviews = cur.fetchall()

    if movie == 'latest': #movie에 latest가 저장되어 있으면 db에서 release된 날짜에 따라 정렬하여 movies에 저장
        cur.execute("WITH avg_rating(id, value) as (select mid, avg(ratings) from reviews group by mid) select title, trunc(value, 1), director, genre, rel_date from movies natural left outer join avg_rating order by rel_date desc;")
        movies = cur.fetchall()
    elif movie == 'genre': #movie에 genre가 저장되어 있으면 db에서 genre에 따라 정렬하여 movies에 저장
        cur.execute("WITH avg_rating(id, value) as (select mid, avg(ratings) from reviews group by mid) select title, trunc(value, 1), director, genre, rel_date from movies natural left outer join avg_rating order by genre;")
        movies = cur.fetchall()
    elif movie == 'ratings': #movie에 ratings가 저장되어 있으면 db에서 평균 ratings값에 따라 정렬하여 movies에 저장
        cur.execute("WITH avg_rating(id, value) as (select mid, avg(ratings) from reviews group by mid) select title, trunc(value, 1) as per_movie_avg_ratings, director, genre, rel_date from movies natural left outer join avg_rating order by per_movie_avg_ratings desc;")
        movies = cur.fetchall()

    if review == 'latest': #review에 latest가 저장되어 있으면 db에서 리뷰를 작성한 날짜에 따라 정렬하여 reviews에 저장(로그인한 사용자가 mute한 사용자는 나타나지 않음)
        cur.execute(f"SELECT A.ratings, A.uid, B.title, A.review, to_char(A.rev_time, 'YYYY-MM-DD HH24:MI'), A.likes_count, A.mid FROM reviews as A, movies as B where A.mid = B.id and A.uid not in (select C.opid from ties as C where C.tie = 'mute' and C.id = '{username}') order by A.rev_time desc;")
        reviews = cur.fetchall()
    elif review == 'title':#review에 title이 저장되어 있으면 db에서 영화 제목에 따라 정렬하여 reviews에 저장(로그인한 사용자가 mute한 사용자는 나타나지 않음)
        cur.execute(f"SELECT A.ratings, A.uid, B.title, A.review, to_char(A.rev_time, 'YYYY-MM-DD HH24:MI'), A.likes_count, A.mid FROM reviews as A, movies as B where A.mid = B.id and A.uid not in (select C.opid from ties as C where C.tie = 'mute' and C.id = '{username}') order by B.title;")
        reviews = cur.fetchall()
    elif review == 'followers':#review에 followers가 저장되어 있으면 db에서 팔로워수에 따라 정렬하여 reviews에 저장(로그인한 사용자가 mute한 사용자는 나타나지 않음)
        cur.execute(f"with follow_num(id, value) as (select opid, count(id) from ties where tie = 'follow' group by opid),follow_numnum(id, value) as (select distinct Z.id, case when Z.id in (select X.id from follow_num as X) then (select V.value from follow_num as V where V.id = Z.id) else 0 end from users as Z) SELECT A.ratings, A.uid, B.title, A.review, to_char(A.rev_time, 'YYYY-MM-DD HH24:MI'), A.likes_count, A.mid FROM reviews as A, movies as B, follow_numnum as C where A.mid = B.id and C.id = A.uid and A.uid not in (select C.opid from ties as C where C.tie = 'mute' and C.id = '{username}') order by C.value desc, A.uid;")
        reviews = cur.fetchall()
    elif review == 'likes':#review에 likes가 저장되어 있으면 db에서 리뷰의 좋아요 수에 따라 정렬하여 reviews에 저장(로그인한 사용자가 mute한 사용자는 나타나지 않음)
        cur.execute(f"SELECT A.ratings, A.uid, B.title, A.review, to_char(A.rev_time, 'YYYY-MM-DD HH24:MI'), A.likes_count, A.mid FROM reviews as A, movies as B where A.mid = B.id and A.uid not in (select C.opid from ties as C where C.tie = 'mute' and C.id = '{username}') order by A.likes_count desc, A.uid;")
        reviews = cur.fetchall()
    return render_template("main.html", username=username, movies=movies, reviews=reviews, movie=movie, review=review)#위 정보들로 main.html을 구성

@app.route('/sort', methods=['get']) #사용자가 원하는 정렬 방법을 버튼을 눌러 설정할 때, 해당 정렬 방법을 각각 movie, review에 저장하여 /main으로 전달
def sort():
    username = request.args['username']
    movie = request.args['movie'] if 'movie' in request.args else 'main' #movie에 대한 정렬 방법을 설정하지 않았을 때 기본값인 main으로 설정
    review = request.args['review'] if 'review' in request.args else 'main' #review에 대한 정렬 방법을 설정하지 않았을 때 기본값인 main으로 설정
    return redirect(url_for('main', username=username, movie=movie, review=review)) #설정한 값들을 /main으로 넘겨 사용자가 원하는 정렬 방식대로 나타나게끔 함

@app.route('/movie', methods=['get', 'post']) #영화 페이지를 보여줌
def movie():
    #사용자id, 영화 제목을 args로 받아옴
    username = request.args['username']
    title = request.args["title"]
    #해당 페이지의 영화의 정보를 db에서 찾아 movies에 저장
    cur.execute(f"SELECT director, genre, rel_date from movies where title = '{title}';")
    movies = cur.fetchall()
    #해당 페이지의 영화의 평균 ratings 값을 db에서 찾아 avg_ratings에 저장 (로그인한 사용자가 mute한 사용자의 rating은 반영되지 않음)
    cur.execute(f"select trunc(avg(ratings),1) from movies, reviews where movies.id = reviews.mid and reviews.uid not in (select C.opid from ties as C where C.tie = 'mute' and C.id = '{username}') group by movies.id having movies.title = '{title}';")
    avg_rating = cur.fetchall()
    #해당 페이지의 영화에 대한 review들을 찾아 reviews에 저장 (로그인한 사용자가 mute한 사용자는 나타나지 않음)
    cur.execute(f"select ratings, uid, review, to_char(rev_time, 'YYYY-MM-DD HH24:MI'), likes_count, movies.id from movies, reviews where movies.id = reviews.mid and reviews.uid not in (select C.opid from ties as C where C.tie = 'mute' and C.id = '{username}') and movies.title = '{title}';")
    reviews = cur.fetchall()
    return render_template("movie.html", username = username, title = title, movies = movies, avg_rating = avg_rating, reviews = reviews)#위 정보들로 movie.html을 구성

@app.route('/submit', methods=['post']) #영화 리뷰 작성 기능
def submit():
    username = request.form['username']
    title = request.form['title']
    rating = request.form['rating']
    text = request.form['review'] #사용자가 작성한 리뷰에 대한 정보들을 각각 title, rating, text에 저장
    #해당 title를 가진 영화의 id를 db에서 찾아 mid 변수에 저장
    cur.execute(f"select id from movies where title = '{title}';")
    mid = cur.fetchall()[0][0]
    #로그인한 사용자가 해당 영화에 대해 리뷰를 작성하였는지 확인하기 위해 sql 명령문을 실행하고 만약 이미 해당 영화에 대한 사용자의 리뷰가 존재한다면 리뷰를 result에 저장
    cur.execute(f"select mid from reviews where mid = '{mid}' and uid = '{username}';")
    result = cur.fetchall()
    if text.replace(' ', '') == '': #사용자가 리뷰를 빈칸으로 제출하였다면 저장 실패하였다는 것을 전달
        return render_template('submit_fail.html', username=username, error_message='리뷰는 빈칸일 수 없습니다.')
    if result != []: #만약 사용자가 이전에 해당 영화에 대해 리뷰를 작성하였다면 그 리뷰와 그 리뷰에 대해 '좋아요'를 한 기록들을 모두 삭제
        cur.execute(f"delete from likes where review_uid = '{username}' and review_mid='{mid}';")
        cur.execute(f"delete from reviews where uid = '{username}' and mid = '{mid[0][0]}';")
    #해당 리뷰를 reviews table에 추가하고 반영
    cur.execute(f"insert into reviews values('{mid[0][0]}','{username}',{rating},'{text}', '{datetime.now()}', 0);")
    connect.commit()
    return redirect(url_for('movie', username = username, title = title)) #작성한 리뷰가 반영된 페이지를 보여주기 위함

@app.route('/user', methods=['get']) #특정 사용자 버튼을 눌렀을 때
def user():
    #username은 로그인한 사용자의 id, search는 정보를 보기 원하는 사용자의 id를 저장
    username = request.args['username'] #
    search = request.args['search']
    #로그인한 사용자의 role을 확인하여
    cur.execute(f"select role from users where id = '{username}';")
    role = cur.fetchall()[0][0]
    if role == 'admin' and username == search: #만약 로그인한 사용자의 role이 admin이고 자신의 페이지를 보고 싶다면
        return redirect(url_for('adminpage', username = username, search = search)) #adminpage url로 이동
    elif username == search: #로그인한 사용자의 role이 user고 자신의 페이지를 보고 싶다면
        return redirect(url_for('mypage', username = username)) #mypage url로 이동
    else: #자신의 페이지가 아닌 다른 사용자의 페이지를 보고 싶다면, userpage url로 이동
        return redirect(url_for('userpage', username = username, search = search))

@app.route('/adminpage', methods=['get']) #관리자 페이지 기능
def adminpage():
    username = request.args['username']
    search = request.args['search']
    #자신이 작성한 리뷰들에 대한 정보를 db에서 찾아 reviews에 저장
    cur.execute(f"select A.ratings, B.title, A.review, to_char(A.rev_time, 'YYYY-MM-DD HH24:MI'), A.likes_count, B.id from reviews as A, movies as B where A.uid = '{username}' and A.mid = B.id;")
    reviews = cur.fetchall()
    return render_template("adminpage.html", username= username, search=search, reviews = reviews) #위 정보들을 adminpage.html로 보내 사용자에게 보여줌

@app.route('/mypage', methods=['get']) #마이 페이지 기능
def mypage():
    username = request.args['username']
    #자신이 작성한 리뷰들을 찾아 reviews에 저장
    cur.execute(f"select A.ratings, B.title, A.review, to_char(A.rev_time, 'YYYY-MM-DD HH24:MI:SS'), likes_count, B.id from reviews as A, movies as B where A.uid = '{username}' and A.mid = B.id;")
    reviews = cur.fetchall()
    #자신을 팔로우하고 있는 사용자들을 db에서 찾아 followers에 저장
    cur.execute(f"select id from ties where opid = '{username}' and tie = 'follow';")
    followers = cur.fetchall()
    #자신이 팔로우하고 있는 사용자들을 db에서 찾아 followeds에 저장
    cur.execute(f"select opid from ties where id = '{username}' and tie = 'follow';")
    followeds = cur.fetchall()
    #자신이 mute하고 있는 사용자들을 db에서 찾아 muteds에 저장
    cur.execute(f"select opid from ties where id = '{username}' and tie = 'mute';")
    muteds = cur.fetchall()
    return render_template("mypage.html", username = username, reviews = reviews, followers = followers, followeds = followeds, muteds = muteds) #위 정보들을 mypage.html로 보내 사용자에게 보여줌

@app.route('/userpage', methods=['get', 'post']) #내가 아닌 다른 사용자의 페이지를 볼 수 있는 기능
def userpage():
    #username은 로그인한 사용자의 id, search는 정보를 보고자 하는 사용자의 id
    username = request.args['username']
    search = request.args['search']
    #search에 해당하는 사용자가 작성한 리뷰들을 db에서 찾아 reviews에 저장
    cur.execute(f"select A.ratings, B.title, A.review, to_char(A.rev_time, 'YYYY-MM-DD HH24:MI'), A.likes_count, B.id from reviews as A, movies as B where A.uid = '{search}' and A.mid = B.id;")
    reviews = cur.fetchall()
    #search에 해당하는 사용자를 팔로우하는 사람들을 db에서 찾아 followers에 저장
    cur.execute(f"select id from ties where opid = '{search}' and tie = 'follow';")
    followers = cur.fetchall()
    #로그인한 사용자의 role을 username_role에 저장
    cur.execute(f"select role from users where id = '{username}';")
    username_role = cur.fetchall()[0][0]
    #search에 해당하는 사용자의 role을 search_role에 저장
    cur.execute(f"select role from users where id = '{search}';")
    search_role = cur.fetchall()[0][0]
    if search_role == 'admin': #정보를 보려고 하는 대상의 role이 admin이라면 useradminpage로 이동(follow, mute버튼이 존재하지 않는 useradminpage.html을 보여줌)
        return render_template("useradminpage.html", username=username, search=search, reviews=reviews)
    elif username_role == 'admin': #로그인한 사용자의 role이 admin이라면 adminuserpage로 이동(admin role을 가진 사용자는 팔로우, 뮤트할 수 없기 때문에 html을 나눔)
        return render_template("adminuserpage.html", username=username, search=search, reviews=reviews, followers=followers)
    else: #username에 해당하는 사용자, search에 해당하는 사용자 모두 role이 admin이 아니라면 userpage.html을 불러옴
        return render_template("userpage.html", username=username, search = search, reviews=reviews, followers=followers)

@app.route('/unfollow', methods=['post']) #unfollow 기능
def unfollow():
    #로그인한 사용자인 username과 대상이 되는 search에 해당하는 사용자의 id를 각각 username과 search에 저장
    username = request.form['username']
    search = request.form['search']
    #db에서 follow 정보를 삭제하고 반영
    cur.execute(f"delete from ties where id = '{username}' and opid = '{search}' and tie = 'follow';")
    connect.commit()
    return redirect(url_for('mypage', username = username))

@app.route('/follow', methods=['post']) #follow 기능
def follow():
    # 로그인한 사용자인 username과 대상이 되는 search에 해당하는 사용자의 id를 각각 username과 search에 저장
    username = request.form['username']
    search = request.form['search']
    #db에서 해당 사용자의 이름을 username과 search에 해당하는 사용자 사이의 관계(follow나 mute)를 찾아보고, 이미 관계가 설정되어 있다면 result에 저장
    cur.execute(f"select id from ties where id = '{username}' and opid = '{search}';")
    result = cur.fetchall()
    if result == []: #follow나 mute 관계가 설정되지 않았다면 db에 해당 follow관계를 저장한 후 반영된 페이지를 보여줌
        cur.execute(f"insert into ties values('{username}', '{search}', 'follow');")
        connect.commit()
        return redirect(url_for('userpage', username = username, search=search))
    else:
        return render_template('submit_fail.html', username=username, error_message='이미 해당 사용자를 follow 중이거나 mute 중입니다.')

@app.route('/mute', methods=['post']) #mute기능
def mute():
    # 로그인한 사용자인 username과 대상이 되는 search에 해당하는 사용자의 id를 각각 username과 search에 저장
    username = request.form['username']
    search = request.form['search']
    # db에서 해당 사용자의 이름을 username과 search에 해당하는 사용자 사이의 mute 여부를 찾아보고, 이미 mute관계가 설정되어 있다면 result에 저장
    cur.execute(f"select id from ties where id = '{username}' and opid = '{search}' and tie = 'mute';")
    result = cur.fetchall()
    if result == []: #mute되지 않은 상태라면
        #follow관계인지 찾아보고 follow관계라면 해당 정보를 check_follow에 저장
        cur.execute(f"select id from ties where id = '{username}' and opid = '{search}' and tie = 'follow';")
        check_follow = cur.fetchall()
        if check_follow != []: #follow관계에 대한 데이터가 존재하면(팔로우 관계라면) 해당 데이터를 삭제
            cur.execute(f"delete from ties where id = '{username}' and opid = '{search}' and tie = 'follow';")
        #mute관계에 대한 data를 저장하고 반영된 페이지를 보여줌
        cur.execute(f"insert into ties values('{username}', '{search}', 'mute');")
        connect.commit()
        return redirect(url_for('userpage', username = username, search=search))
    return render_template('submit_fail.html', username=username, error_message='이미 해당 사용자를 mute 하고 있습니다.')

@app.route('/unmute', methods=['post']) #unmute기능
def unmute():
    #로그인한 사용자인 username과 대상이 되는 search에 해당하는 사용자의 id를 각각 username과 search에 저장
    username = request.form['username']
    search = request.form['search']
    #username과 search 사용자끼리의 mute관계를 db에서 찾아 해당 데이터를 삭제하고 반영된 페이지를 보여줌
    cur.execute(f"delete from ties where id = '{username}' and opid = '{search}' and tie = 'mute';")
    connect.commit()
    return redirect(url_for('mypage', username = username))

@app.route('/add', methods=['post']) #admin 사용자가 새로운 영화를 추가하는 기능
def add():
    #사용자 정보 및 영화에 대한 정보들을 form형식으로 불러온 후 각각의 변수에 저장
    username = request.form['username']
    search = request.form['search']
    title = request.form['title']
    director = request.form['director']
    genre = request.form['genre']
    rel_date = request.form['rel_date']
    #이미 같은 영화가 저장되어 있는지 확인하기 위해 해당 영화의 제목으로 된 영화를 db에서 찾고 그 결과를 result에 저장
    cur.execute(f"select title from movies where title = '{title}'")
    result = cur.fetchall()
    if result == [] and title.replace(' ', '') != '' and director.replace(' ', '') != '' and rel_date.replace(' ', '') != '': #해당 title의 영화가 db에 존재하지 않으면서 영화 정보에 빈칸이 존재하지 않는다면 db에 영화 정보를 저장하고 반영
        cur.execute("select max(id) from movies") #새 영화의 id는 현재 db에 있는 id의 최댓값보다 1 큰 id로 설정
        max_id = cur.fetchall()
        id = str(int(max_id[0][0]) + 1)
        cur.execute(f"insert into movies values('{id}', '{title}', '{director}', '{genre}', '{rel_date}');")
        connect.commit()
        return redirect(url_for("user", username = username, search = search))
    else: #이미 같은 제목의 영화가 존재하거나 빈칸이 있다면 해당 오류를 사용자에게 전달
        if result != []:
            return render_template('submit_fail.html', username=username, error_message='이미 같은 제목의 영화가 존재합니다.')
        elif title.replace(' ', '') == '':
            return render_template('submit_fail.html', username=username, error_message='제목은 빈칸일 수 없습니다.')
        elif director.replace(' ', '') == '':
            return render_template('submit_fail.html', username=username, error_message='감독 이름은 빈칸일 수 없습니다.')
        elif rel_date.replace(' ', '') == '':
            return render_template('submit_fail.html', username=username, error_message='개봉 날짜는 빈칸일 수 없습니다.')




@app.route('/like', methods=['post']) #특정 사용자가 작성한 리뷰에 '좋아요'를 할 수 있는 기능
def like():
    #로그인한 사용자의 id를 username, 좋아요를 누르려는 리뷰의 사용자 id를 review_uid, 리뷰의 영화 id를 review_mid에 저장하고 현재 어떤 페이지에서 이 기능이 사용되었는지를 page에 저장
    username = request.form['username']
    review_uid = request.form['review_uid']
    review_mid = request.form['review_mid']
    page = request.form['page']
    #이미 좋아요를 눌렀는지 확인하기 위하여 db에서 해당 id, review_uid, review_mid로 된 데이터가 있는지 확인하고 있다면 result에 저장
    cur.execute(f"select id, review_uid, review_mid from likes where id = '{username}' and review_uid = '{review_uid}' and review_mid = '{review_mid}';")
    result = cur.fetchall()
    if result == [] and username != review_uid: #이전에 좋아요를 누르지 않았고 자신의 리뷰도 아니라면 좋아요를 누를 수 있으므로 db에 좋아요 데이터를 저장하고, 해당 리뷰의 좋아요 수를 1 증가시킴
        cur.execute(f"insert into likes values('{username}', '{review_uid}', '{review_mid}');")
        cur.execute(f"update reviews set likes_count = likes_count + 1 where uid = '{review_uid}' and mid = '{review_mid}';")
        connect.commit()
        #좋아요 수를 업데이트한 결과를 사용자가 좋아요를 누른 페이지에 따라 반영
        if page == 'main':
            return redirect(url_for("main", username = username, movie = 'main', review = 'main'))
        elif page == 'movie':
            cur.execute(f"select title from movies where id = '{review_mid}'")
            title = cur.fetchall()[0][0]
            return redirect(url_for("movie", username = username, title = title))
        else:
            return redirect(url_for("userpage", username = username, search = review_uid))
    else: #좋아요를 누를 수 없다면 해당 오류를 사용자에 전달
        if result != []:
            return render_template('submit_fail.html', username=username, error_message = '이미 해당 리뷰에 대해 좋아요를 누르셨습니다.')
        elif username == review_uid:
            return render_template('submit_fail.html', username=username, error_message = '자신의 리뷰에 좋아요를 누를 수 없습니다.')


#my review delete
@app.route('/delete', methods=['post']) #작성한 리뷰 삭제 기능
def delete():
    #로그인한 사용자 id와 리뷰 삭제하려는 영화의 id를 불러옴
    username = request.form['username']
    mid = request.form['review_mid']
    #해당 리뷰에 좋아요를 누른 데이터를 삭제하고, 그 다음 리뷰 자체에 대한 정보를 삭제하고 반영한 결과를 사용자에 보여줌
    cur.execute(f"delete from likes where review_uid = '{username}' and review_mid='{mid}';")
    cur.execute(f"delete from reviews where uid = '{username}' and mid = '{mid}';")
    connect.commit()
    return redirect(url_for("mypage", username = username))


if __name__ == '__main__':
    app.run()
