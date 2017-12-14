import sys,os,datetime, time
from calendar import timegm
from flask import render_template, redirect, request, url_for, flash,send_file, send_from_directory,current_app,g
from werkzeug import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from .. import db
from ..models import Director, Student, UploadFiles, AddStudent
from ..email import send_email
from .forms import LoginForm, ReqForm, RegistrationForm, DirectorRegistrationForm, StudentRegistrationForm, AddStudentForm, \
    GridForm, RowForm, EmailProfessorForm, AddStudentToClassForm, SearchStudentsRowForm, SearchStudentsGridForm, ProfessorForm, \
    StudentHomeworkRowForm, StudentHomeworkGridForm, AddHomeworkForm
from sqlalchemy import text

from app import create_app
app = create_app(os.getenv('FLASK_CONFIG') or 'default')
global g_director_id,g_student_id,g_director_name,g_student_name
g_director_id = None
g_director_name = None
g_student_id = None
g_student_name = None

with app.app_context():

    UPLOAD_FOLDER = current_app.config.get('UPLOAD_FOLDER')
    DOWNLOAD_FOLDER = current_app.config.get('UPLOAD_FOLDER')
    ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

@auth.route('/DirectorLogin', methods=['GET', 'POST'])
def DirectorLogin():
    global g_director_id, g_director_name
    form = LoginForm()
    if form.validate_on_submit():
        user = Director.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            director = Director.query.filter_by(email=form.email.data).first()
            g_director_id = director.id
            g_director_name = director.first_name + " " + director.last_name
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('auth.DirectorMenu'))
        flash('Invalid username or password.')
    return render_template('auth/DirectorLogin.html', form=form)

@auth.route('/StudentLogin', methods=['GET', 'POST'])
def StudentLogin():
    global g_student_id
    form = LoginForm()
    if form.validate_on_submit():
        user = Student.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            g_student_id = user.id
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('auth.StudentMenu'))
            #return redirect(request.args.get('next') or url_for('auth.show_files'))
        flash('Invalid username or password.')
    return render_template('auth/StudentLogin.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))

@auth.route('/RegisterDirector', methods=['GET', 'POST'])
def RegisterDirector():
    form = DirectorRegistrationForm()
    if form.validate_on_submit():
        director = Director(first_name=form.first_name.data,
                       last_name=form.last_name.data,
                        email=form.email.data,
                        username=form.username.data,
                        password=form.password.data)
        db.session.add(director)
        flash('You can now login.')
        return redirect(url_for('auth.DirectorLogin'))
    return render_template('auth/RegisterDirector.html', form=form)

@auth.route('/RegisterStudent', methods=['GET', 'POST'])
def RegisterStudent():
    form = StudentRegistrationForm()
    if form.validate_on_submit():
        student = Student(first_name=form.first_name.data,
                       last_name=form.last_name.data,
                       email=form.email.data,
                    username=form.username.data,
                    password=form.password.data)
        db.session.add(student)
        flash('You can now login.')
        return redirect(url_for('auth.StudentLogin'))
    return render_template('auth/RegisterStudent.html', form=form)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@auth.route("/upload", methods=['GET', 'POST'])
def upload():
    hw_list = []
    sql = ("select hw_name from web.homeworks where director_id = " + str(g_director_id))
    result = db.engine.execute(sql)
    for row in result:
        hw_list.append(row[0])
    return render_template('auth/upload.html', hw_list = hw_list)

@auth.route('/uploader', methods = ['GET', 'POST'])
def uploader():
   if request.method == 'POST':
      sql = ("select id from web.homeworks where director_id = " + str(g_director_id) + " and hw_name = '" + request.form['homework'] + "'")
      result = db.engine.execute(sql)
      for row in result:
          hw_id = row[0]
      f = request.files['file']
      filename = secure_filename(f.filename)
      STATIC_FOLDER = os.path.abspath("./" + "/app/static")
      f.save(os.path.join(STATIC_FOLDER, filename))
      hw_create_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      sql = ("insert into web.upload_files (file_name, file_location, director_id, hw_create_time, hw_id) values('" + filename + "','" + STATIC_FOLDER + "'," + str(g_director_id) + ",'" + hw_create_time + "'," + str(hw_id) + ")")
      db.engine.execute(sql)
      return 'file uploaded successfully'

@auth.route("/ChoseProfessor", methods=['GET', 'POST'])
def ChoseProfessor():
    global g_professor_id
    professor_list = []
    sql =  ("select CONCAT(d.first_name, ' ', d.last_name, ' - ', d.email) "
            "from web.director d "
            "join web.director_student ds on ds.director_id = d.id "
            " where ds.student_id = " + str(g_student_id))

    result = db.engine.execute(sql)
    for row in result:
        professor_list.append(row[0])

    if request.method == 'POST':
        professor_name = request.form['professor']
        professor_email = professor_name.split("-")[1].strip()
        sql = ("select id from web.director where email = '" + professor_email + "'")
        result = db.engine.execute(sql)
        for row in result:
            g_professor_id = row[0]
        hw_list = []
        sql = ("select hw_name from web.homeworks where director_id  = " + str(g_professor_id))
        result = db.engine.execute(sql)
        for row in result:
            hw_list.append(row[0])
        return render_template('auth/UploadStudentFiles.html',hw_list = hw_list)
    return render_template('auth/ChoseProfessor.html', professor_list = professor_list)

@auth.route("/UploadStudentFiles", methods=['GET', 'POST'])
def UploadStudentFiles():
    return render_template('auth/UploadStudentFiles.html')

# Inserts student files in the database. Called from UploadStudentFiles.html
@auth.route('/StudentFileUploader', methods = ['GET', 'POST'])
def StudentFileUploader():
   if request.method == 'POST':
      hw_name = request.form['homework']
      sql = ("select id,hw_deadline from web.homeworks where director_id = " + str(g_professor_id) + " and hw_name = '" + hw_name.strip() + "'")
      result = db.engine.execute(sql)
      for row in result:
        hw_id = row[0]
        hw_deadline = row[1]
      current_time_epoch = int(time.time())
      utc_time = time.strptime(str(hw_deadline), "%Y-%m-%d %H:%M:%S")
      hw_deadline_epoch = timegm(utc_time)
      if current_time_epoch > hw_deadline_epoch:
         return "Current time is past deadline: " +  str(hw_deadline) + ". Homework cannot be uploaded."

      f = request.files['file']
      filename = secure_filename(f.filename)
      STATIC_FOLDER = os.path.abspath("./" + "/app/static")
      f.save(os.path.join(STATIC_FOLDER, filename))
      sql = text('select id from web.student_files where file_name = \'' +str(filename) + '\' and file_location = \'' + STATIC_FOLDER + '\' and student_id = ' + str(g_student_id) + '')
      result = db.engine.execute(sql)
      rec_id = None
      for row in result:
          rec_id = row[0]
      if rec_id is not None:
          sql = text('delete from web.student_files where id = ' + str(rec_id) + '')
          db.engine.execute(sql)
      sql = text('insert into web.student_files (file_name,file_location,student_id,hw_id) values(\'' + filename + '\',\'' + STATIC_FOLDER + '\',' + str(g_student_id) + ',' + str(hw_id) + ')')
      result = db.engine.execute(sql)
      return 'file uploaded successfully'

@auth.route("/AddStudent", methods=['GET', 'POST'])
def AddStudent():
    form = AddStudentToClassForm()
    if request.method == 'POST':
        email = form.data['email'].strip()
        if len(form.data['email'].strip()) > 0:
            sql = ("select id, first_name, last_name "
                   "from web.student "
                   "where email = '" + str(email)) + "'"
            result = db.engine.execute(sql)
            if result is not None:
                if result.rowcount == 0:
                    return "There are no registered users having email: " + email
                elif result.rowcount > 1:
                    return "There are multiple registered users having email: " + email
                for row in result:
                    student_id = row[0]
                    first_name = row[1]
                    last_name = row[2]
        else:
            first_name = form.data['first_name'].strip()
            last_name = form.data['last_name'].strip()
            if (len(first_name) > 0) and (len(last_name) > 0):
                sql = ("select id, email "
                       "from web.student "
                       "where first_name = '" + str(first_name)) + "' and last_name = '" + str(last_name) +"'"
                result = db.engine.execute(sql)
                if result is not None:
                    if result.rowcount == 1:
                        for row in result:
                            student_id = row[0]
                            email = row[1]
                    else:
                        if result.rowcount == 0:
                            return "There are no registered users having first name: " + str(first_name) + " and last name: " +  str(last_name)
                        return "There are more than one registered users having first name: " + str(first_name) + " and last name: " + str(last_name)

        # If we got here we have a student_id
        sql = text('select id from web.director_student where director_id = ' + str(g_director_id) + ' and student_id = ' + str(student_id))
        result = db.engine.execute(sql)
        if result.rowcount == 0:
            sql = text('insert into web.director_student (director_id,student_id) values(' + str(g_director_id) + ',' + str(student_id) + ')')
            result = db.engine.execute(sql)
        else:
            return "Student: " + first_name + " " + last_name + " is already added to class."
        return redirect(url_for('auth.AddStudent'))
    return render_template('auth/AddStudent.html', form=form)

@auth.route("/AssignFilesToStudents", methods=['GET', 'POST'])
def AssignFilesToStudents():
    form = AddStudentForm()
    fileList = []
    fileList.append('file1.txt')
    fileList.append('file2.txt')
    if form.validate_on_submit():
        selected_users = request.form.getlist("users")
    return render_template('auth/AssignFilesToStudents.html', form=form,fileList=fileList)

@auth.route("/UpdateStudentPermissions", methods=['GET', 'POST'])
def UpdateStudentPermissions():
    # Update database records
    return redirect(url_for('auth.AddStudent'))

@auth.route("/ShowFiles", methods=['GET', 'POST'])
def show_files():
    sql = text('select file_name from upload_files where director_id in \
       (select director_id from web.director_student where student_id = ' + str(g_student_id) +')')
    result = db.engine.execute(sql)
    fileList =[]
    for row in result:
        fileList.append(row[0])
    return render_template('auth/ShowFiles.html', fileList=fileList)

# To be deployed later
@auth.route("/PracticeMusic", methods=['GET', 'POST'])
def PracticeMusic():
    pass #place holder
    return render_template('auth/PracticeMusic.html')

# To be deployed later
@auth.route("/UploadNewRecording", methods=['GET', 'POST'])
def UploadNewRecording():
    pass #place holder
    return render_template('auth/UploadNewRecording.html')

# To be deployed later
@auth.route("/EmailProfessor", methods=['GET', 'POST'])
def EmailProfessor():
    form = EmailProfessorForm()
    if request.method == 'POST':
        if len(form.data['email'].strip()) > 0:
            # Email has already been validate. Send email.
            email = form.data['email'].strip()
            sql = ("select count(*) "
                   "from web.director "
                   "where email = '" + str(email)) + "'"
            result = db.engine.execute(sql)
            if result is not None:
                for row in result:
                    nr_rec = row[0]
                if nr_rec == 0:
                    return "There are no registered users having email: " + email
                elif nr_rec > 1:
                    return "There are multiple registered users having email: " + email
        else:
            first_name = form.data['first_name'].strip()
            last_name = form.data['last_name'].strip()
            if (len(first_name) > 0) and (len(last_name) > 0):
                sql = ("select email "
                       "from web.director "
                       "where first_name = '" + str(first_name)) + "' and last_name = '" + str(last_name) +"'"
                result = db.engine.execute(sql)
                if result is not None:
                    if result.rowcount == 1:
                        for row in result:
                            email = row[0]
                        ## Review the components of the message.
                        #send_email(email, 'New User', 'mail/new_user', user=user)
                    else:
                        if result.rowcount == 0:
                            return "There are no registered users having first name: " + str(first_name) + " and last name: " +  str(last_name)
                        return "There are more than one registered users having first name: " + str(first_name) + " and last name: " + str(last_name)
        # If we reach this line, we have a valid email
        send_email(email, 'Test message', 'This is a test message.', user='NewUser')
        return redirect(url_for('auth.EmailProfessor'))
    return render_template('auth/EmailProfessor.html', form = form)

# Processing professor related options
@auth.route("/DirectorMenu", methods=['GET', 'POST'])
def DirectorMenu():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            return redirect(url_for('auth.DirectorMenu'))
    return render_template('auth/DirectorMenu.html')

@auth.route("/ProfessorReviewFiles", methods=['GET', 'POST'])
def ProfessorReviewFiles():
    submitForm = ReqForm()
    teamform = GridForm()
    teamform.title.data = g_director_name

    sql = ("select sf.id, sf.file_name, CONCAT(st.first_name, ' ', st.last_name), sf.reviewed, sf.grade,sf.notes "
        "from web.student_files sf "
        "join web.student st on sf.student_id = st.id "
        "join web.director_student ds on sf.student_id = ds.student_id "
        "where ds.director_id = " + str(g_director_id) + " order by sf.reviewed DESC")
    result = db.engine.execute(sql)

    for member in result:
        member_form = RowForm()
        member_form.id = str(member[0])
        member_form.file_name = member[1]
        member_form.student_name = member[2]
        if member[3] == 0:
            member_form.status = 'REVIEWED'
        else:
            member_form.status = 'NOT REVIEWED'
        member_form.grade = member[4]
        member_form.notes = member[5]

        teamform.grid.append_entry(member_form)

    if request.method == 'POST':
        if request.form['selected_file'] is None or len(request.form['selected_file']) == 0:
            return "Please enter file name."
        selected_file = request.form['selected_file']
        if request.form['btn'] == 'Review file':
            sql = ("update web.student_files set reviewed = 0, updated = NOW() where file_name = '" + selected_file + "'")
            result = db.engine.execute(sql)
            STATIC_FOLDER = os.path.abspath("./" + "/app/static")
            return send_from_directory(directory=STATIC_FOLDER, filename=selected_file)
        ##if request.form['btn'] == 'Mark reviewed':
        ##    sql = ("update web.student_files set reviewed = 0, updated = NOW() where file_name = '" + selected_file + "'")
            result = db.engine.execute(sql)
        if request.form['btn'] == 'Grade':
            if request.form['grade'] is None or len(request.form['grade']) == 0:
               return "Grade has to be between 0 and 100"
            sql = ("update web.student_files set grade = " + str(request.form['grade']) + ", time_graded = NOW() where file_name = '" + selected_file + "'")
            result = db.engine.execute(sql)
            ##if request.form['btn'] == 'Add notes':
            if request.form['notes'] is not None:
                sql = ("update web.student_files set notes = '" + str(request.form['notes']) + "' where file_name = '" + selected_file + "'")
            result = db.engine.execute(sql)

        return redirect(url_for('auth.ProfessorReviewFiles'))
    return render_template('auth/ProfessorReviewFiles.html', teamform = teamform, submitForm = submitForm)

@auth.route("/SearchStudents", methods=['GET', 'POST'])
def SearchStudents():
    search_student_form = SearchStudentsGridForm()
    search_student_form.title.data = str(g_director_name)

    sql =   ("select st.first_name, st.last_name, st.email "
        "from web.student st "
        "   join web.director_student ds on st.id = ds.student_id "
        "where ds.director_id = " +str(g_director_id))
    print(sql) ##
    result = db.engine.execute(sql)
    for member in result:
        member_form = SearchStudentsRowForm()
        member_form.first_name = member[0]
        member_form.last_name = member[1]
        member_form.email = member[2]
        search_student_form.grid.append_entry(member_form)

    return render_template('auth/SearchStudents.html', search_student_form = search_student_form)

@auth.route("/StudentMenu", methods=['GET', 'POST'])
def StudentMenu():
    if request.method == 'POST':
        return redirect(url_for('auth.StudentMenu'))
    return render_template('auth/StudentMenu.html')

@auth.route("/SearchProfessor", methods=['GET', 'POST'])
def SearchProfessor():
    global g_professor_id
    form = ProfessorForm()
    if request.method == 'POST':
        if len(request.form['email']) > 0:
            sql =  ("select id from web.director where email = '" + str(request.form['email']) + "'")
            result = db.engine.execute(sql)
            if result is not None:
                for row in result:
                    g_professor_id = row[0]
        return redirect(request.args.get('next') or url_for('auth.StudentReviewHomework'))
    return render_template('auth/SearchProfessor.html', form = form)

@auth.route("/StudentReviewHomework", methods=['GET', 'POST'])
def StudentReviewHomework():

    sql =   ("select CONCAT(first_name, ' ', last_name) from web.director where id = " +str(g_professor_id))
    result = db.engine.execute(sql)
    professor_name = ""
    for row in result:
        professor_name = row[0]

    form = StudentHomeworkGridForm()
    form.title.data = professor_name

    sql =   ("select uf.file_name, hw.hw_name "
             "from web.upload_files uf "
             "join web.director d on d.id = uf.director_id "
             "join web.homeworks hw on uf.hw_id = hw.id "
             "where d.id = " + str(g_professor_id))

    result = db.engine.execute(sql)

    for member in result:
        member_form = StudentHomeworkRowForm()
        member_form.file_name = str(member[0])
        member_form.hw_name = member[1]

        form.grid.append_entry(member_form)

    if request.method == 'POST':
        if request.form['selected_file'] is None or len(request.form['selected_file']) == 0:
            return "Please enter file name."
        selected_file = request.form['selected_file']
        if request.form['btn'] == 'Review file':
            STATIC_FOLDER = os.path.abspath("./" + "/app/static")
            return send_from_directory(directory=STATIC_FOLDER, filename=selected_file)
        """
        if request.form['btn'] == 'Mark reviewed':
            sql = ("update web.student_files set reviewed = 0, updated = NOW() where file_name = '" + selected_file + "'")
            result = db.engine.execute(sql)
        if request.form['btn'] == 'Grade':
            if request.form['grade'] is None or len(request.form['grade']) == 0:
               return "Grade has to be between 0 and 100"
            sql = ("update web.student_files set grade = " + str(request.form['grade']) + ", time_graded = NOW() where file_name = '" + selected_file + "'")
            result = db.engine.execute(sql)
        if request.form['btn'] == 'Add notes':
            if request.form['notes'] is not None:
                sql = ("update web.student_files set notes = '" + str(request.form['notes']) + "' where file_name = '" + selected_file + "'")
            result = db.engine.execute(sql)
        """
        return redirect(url_for('auth.StudentReviewHomework'))
    return render_template('auth/StudentReviewHomework.html', StudentHomeworkGridForm = form)

@auth.route("/ProfessorAddHomework", methods=['GET', 'POST'])
def ProfessorAddHomework():
    form = AddHomeworkForm()
    if request.method == 'POST':
        hw_name = request.form['hw_name']
        sql = ("select count(*) from web.homeworks where director_id = " + str(g_director_id) + " and hw_name = '" + hw_name + "'")
        result = db.engine.execute(sql)
        for row in result:
            rec_count = row[0]
        if rec_count > 0:
            return "There is already a homework called: " + hw_name + " for professor id: " + str(g_director_id)
        date_due = request.form['date_due']
        sql = ("insert into web.homeworks (director_id,hw_name,hw_deadline) values (" + str(g_director_id) + ",'" + hw_name + "','" + date_due.strip() + "')")
        result = db.engine.execute(sql)

    return render_template('auth/ProfessorAddHomework.html', form = form)

@auth.route("/StudentChoseProfessorReviewHomework", methods=['GET', 'POST'])
def StudentChoseProfessorReviewHomework():
    global g_professor_id
    professor_list = []
    sql =  ("select CONCAT(d.first_name, ' ', d.last_name, ' - ', d.email) "
            "from web.director d "
            "join web.director_student ds on ds.director_id = d.id "
            " where ds.student_id = " + str(g_student_id))

    result = db.engine.execute(sql)
    for row in result:
        professor_list.append(row[0])
    if request.method == 'POST':
        professor_name = request.form['professor']
        professor_email = professor_name.split("-")[1].strip()
        sql = ("select id from web.director where email = '" + professor_email + "'")
        result = db.engine.execute(sql)
        for row in result:
            g_professor_id = row[0]
        return redirect(request.args.get('next') or url_for('auth.StudentReviewHomework'))
    return render_template('auth/StudentChoseProfessorReviewHomework.html', professor_list=professor_list)