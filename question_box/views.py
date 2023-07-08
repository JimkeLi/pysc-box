from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext as _

from . import models
import json
import datetime


def index(request):

    # Users,therapists and administrator would see different pages (the superuser's id is 1)
    if request.user.id == 1:
        user = models.User.objects.get(id=request.user.id)
    elif not request.user.is_authenticated:
        user = None
    else:
        user = models.NewUser.objects.get(id=request.user.id)
    return render(request, "question_box/index.html", {
        "user": user,
        "request": request,
        "lang": "en"
    })


'''def index_lang(request, lang):

    # Users,therapists and administrator would see different pages (the superuser's id is 1)
    if request.user.id == 1:
        user = models.User.objects.get(id=request.user.id)
    elif not request.user.is_authenticated:
        user = None
    else:
        user = models.NewUser.objects.get(id=request.user.id)
    return render(request, "question_box/index.html", {
        "user": user,
        "request": request,
        "lang": lang
    })'''


def all_questions(request):

    # Users,therapists and administrator would see different pages (the superuser's id is 1)
    if request.user.id == 1:
        user = models.User.objects.get(id=request.user.id)
    elif not request.user.is_authenticated:
        user = None
    else:
        user = models.NewUser.objects.get(id=request.user.id)

    # Show all the boxes of posted questions and answers
    Boxes = models.Boxes.objects.all()
    boxes = posted(Boxes, "Posted_Part")
    boxes = reversed(boxes)

    return render(request, "question_box/all_questions.html", {
        "boxes": boxes,
        "user": user,
        "request": request
    })


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "question_box/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "question_box/login.html")


def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")

        # Ensure password matches confirmation
        password = request.POST.get("password")
        confirmation = request.POST.get("confirmation")
        if password != confirmation:
            return render(request, "question_box/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = models.NewUser.objects.create_user(
                username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "question_box/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "question_box/register.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


@login_required(login_url="/login")
def ask(request):
    user = models.NewUser.objects.get(id=request.user.id)
    if request.method == "GET":
        return render(request, "question_box/ask.html", {
            "user": user,
            "request": request
        })

    if request.method == "POST":
        question = request.POST.get("question")
        topic = request.POST.get("topic")
        timestamp = datetime.datetime.now()

        '''Assign the box to corresponding ther in turn; The first question of topic "A" is assigned to the first thera of topic "A", 
        the second question to the second thera and so forth; when all theras are used up, it starts from the beginning again'''
        boxes = models.Boxes.objects.filter(topic=topic)
        theras_qset = models.NewUser.objects.filter(
            user_type="thera", topic=topic)
        theras = []
        confirmed_by = models.NewUser.objects.filter(topic="confirm")[0]

        for thera in theras_qset:
            theras.append(thera)

        leng = len(boxes)

        if leng != 0:
            last_box = boxes[leng-1]
            last_thera = last_box.answered_by

            index = theras.index(last_thera)

            if index == (len(theras)-1):
                answered_by = theras[0]
            else:
                answered_by = theras[index+1]

            box = models.Boxes(asked_by=user, answered=False,
                               topic=topic, answered_by=answered_by, confirmed_by=confirmed_by)
            box.save()
            Question = models.Questions(
                question=question, box=box, timestamp=timestamp)
            Question.save()
            return HttpResponseRedirect(reverse("ask"))

        else:
            answered_by = theras[0]
            box = models.Boxes(asked_by=user, answered=False,
                               topic=topic, answered_by=answered_by, confirmed_by=confirmed_by)
            box.save()
            Question = models.Questions(
                question=question, box=box, timestamp=timestamp)
            Question.save()
            return HttpResponseRedirect(reverse("ask"))


@login_required(login_url="/login")
@csrf_exempt
def my_questions(request):
    user = models.NewUser.objects.get(id=request.user.id)
    if user.user_type == "user":
        Boxes = models.Boxes.objects.filter(asked_by=user)
        boxes = serialize(Boxes)
        boxes = reversed(boxes)
        if request.method == "GET":
            return render(request, "question_box/my_questions.html", {
                "user": user,
                "boxes": boxes,
                "request": request
            })

        # Continue the previous questions
        elif request.method == "POST":
            question = request.POST.get("question")
            timestamp = datetime.datetime.now()
            box = models.Boxes.objects.get(id=request.POST.get("box_id"))
            box.answered = False
            box.save()

            # Store the new question asked
            Question = models.Questions(
                question=question, box=box, timestamp=timestamp)
            Question.save()
            Boxes = models.Boxes.objects.filter(asked_by=user)
            boxes = serialize(Boxes)
            return HttpResponseRedirect(reverse("my_questions"))

        # Edit the questions asked
        elif request.method == "PUT":
            data = json.loads(request.body)
            if data.get("question") is not None and data.get("question_id") is not None:
                question = models.Questions.objects.get(
                    id=int(data["question_id"]))
                question.question = data["question"]
                question.post = False
                question.edited = True
                question.save()
                return HttpResponse(status=204)

    else:
        return render(request, "question_box/login.html", {
            "message": "Only the administrator and therapists could have access to this page!"
        })


@login_required(login_url="/login")
def therapists(request):
    user = models.NewUser.objects.get(id=request.user.id)
    theras = models.NewUser.objects.filter(user_type="thera").values()

    # Only the admin can view this page
    if user.user_type == "admin":
        return render(request, "question_box/therapists.html", {
            "user": user,
            "theras": theras,
            "request": request
        })
    else:
        return render(request, "question_box/login.html", {
            "message": "Only the administrator could have access to this page!"
        })


@login_required(login_url="/login")
def create_t(request):
    user = models.NewUser.objects.get(id=request.user.id)

    # Only the admin could view this page
    if user.user_type == 'admin':
        if request.method == "GET":
            return render(request, "question_box/create_t.html", {
                "user": user
            })
        else:
            username = request.POST.get("username")
            email = request.POST.get("email")

            # Ensure password matches confirmation
            password = request.POST.get("password")
            confirmation = request.POST.get("confirmation")
            topic = request.POST.get("topic")

            if password != confirmation:
                return render(request, "question_box/create_t.html", {
                    "message": "Passwords must match.",
                    "user": user,
                    "request": request
                })

            # Attempt to create new therapist
            try:
                new_user = models.NewUser.objects.create_user(
                    username, email, password)
                new_user.user_type = "thera"
                new_user.topic = topic
                new_user.save()
            except IntegrityError:
                return render(request, "question_box/create_t.html", {
                    "message": "Username already taken.",
                    "user": user
                })
            return HttpResponseRedirect(reverse("therapists"))

    else:
        return render(request, "question_box/login.html", {
            "message": "Only the administrator could have access to this page!"
        })


@login_required(login_url="/login")
@csrf_exempt
def post(request, post):
    user = models.NewUser.objects.get(id=request.user.id)

    if user.user_type == "admin":

        if request.method == "GET":
            Boxes = models.Boxes.objects.all()

            if post == "posted":
                boxes = posted(Boxes, "Posted_Full")
                boxes = reversed(boxes)
                return render(request, "question_box/post.html", {
                    "boxes": boxes,
                    "user": user,
                    "request": request,
                    "title": "posted"
                })

            elif post == "unposted":
                boxes = posted(Boxes, "Unposted_Full")
                boxes = reversed(boxes)
                return render(request, "question_box/post.html", {
                    "boxes": boxes,
                    "user": user,
                    "request": request,
                    "title": "unposted"
                })

            else:
                return HttpResponse(status=404)

        # PUT method identifies whether the question should be posted
        elif request.method == "PUT":

            if post == "fetch":
                data = json.loads(request.body)

                if data.get("question_id") is not None:
                    question = models.Questions.objects.get(
                        id=int(data["question_id"]))
                    question.post = data["post"]
                    question.save()
                    if_post = data["post"]

                    if if_post:
                        return HttpResponseRedirect(reverse("post/posted"))
                    else:
                        return HttpResponseRedirect(reverse("post/unposted"))

                elif data.get("answer_id") is not None:
                    answer = models.Answers.objects.get(
                        id=int(data["answer_id"]))
                    answer.post = data["post"]
                    answer.save()
                    if_post = data["post"]

                    if if_post:
                        return HttpResponseRedirect(reverse("post/posted"))
                    else:
                        return HttpResponseRedirect(reverse("post/unposted"))

                else:
                    return JsonResponse({"error": "Invalid Request."}, status=400)

            else:
                return HttpResponse(status=404)

        else:
            return JsonResponse({"error": "Invalid Method."}, status=400)
    else:
        return render(request, "question_box/login.html", {
            "message": "Only the administrator and therapists could have access to this page!"
        })


@login_required(login_url="/login")
@csrf_exempt
def assign(request, assign):
    user = models.NewUser.objects.get(id=request.user.id)

    # Only the admin could view this page
    if user.user_type == "admin":
        theras = models.NewUser.objects.filter(user_type="thera")

        if assign == "unassigned":

            # Get method allows the admin to view the page that assigns questions to therapists
            if request.method == "GET":
                Boxes = models.Boxes.objects.filter(answered_by=None)
                boxes = serialize(Boxes)
                boxes = reversed(boxes)
                return render(request, "question_box/assign.html", {
                    "boxes": boxes,
                    "user": user,
                    "request": request,
                    "theras": theras,
                    "title": "unassigned"
                })

            else:
                return JsonResponse({"error": "Invalid Request."}, status=400)

        if assign == "assigned":

            # Get method allows the admin to view the page that assigns questions to therapists
            if request.method == "GET":
                Boxes = models.Boxes.objects.exclude(answered_by=None)
                boxes = serialize(Boxes)
                boxes = reversed(boxes)
                return render(request, "question_box/assign.html", {
                    "boxes": boxes,
                    "user": user,
                    "request": request,
                    "theras": theras,
                    "title": "assigned"
                })

            else:
                return JsonResponse({"error": "Invalid Request."}, status=400)

        # POST method assigns the questions to therpiasts
        elif assign == "fetch":
            if request.method == "POST":
                data = json.loads(request.body)
                if data.get("answered_by") is not None and data.get("box_id") is not None and data.get("confirmed_by") is not None:
                    box = models.Boxes.objects.get(id=int(data["box_id"]))
                    answered_by = models.NewUser.objects.get(
                        username=data["answered_by"])
                    confirmed_by = models.NewUser.objects.get(
                        username=data["confirmed_by"])
                    box.answered_by = answered_by
                    box.confirmed_by = confirmed_by
                    box.save()
                    return HttpResponse(status=204)
            else:
                return JsonResponse({"error": "Invalid Request."}, status=400)

        else:
            return JsonResponse({
                "error": "Invalid URL."
            }, status=404)

    else:
        return render(request, "question_box/login.html", {
            "message": "Only the administrator and therapists could have access to this page!"
        })


@login_required(login_url="/login")
@csrf_exempt
def answer(request, username, answer):

    # The user that is submitting the request
    request_user = models.NewUser.objects.get(id=request.user.id)

    # The user that request.user is requesting to access to
    user = models.NewUser.objects.get(username=username)

    if answer == "unanswered":

        # Only theras and admin could enter this page
        if user.user_type == "thera":
            if request.method == "GET":

                # The therapists could only have access to their own pages, administrator have access to all pages（In this case the administrator is accessing the page by directly typing in url）
                if request_user.username == user.username or request_user.user_type == "admin":

                    # GET method shows the Boxes that needs to be answered
                    Boxes = models.Boxes.objects.filter(answered_by=user)
                    boxes = answered(Boxes, False)
                    boxes = reversed(boxes)
                    return render(request, "question_box/answer.html", {
                        "boxes": boxes,
                        "user": user,
                        "request": request,
                        "title": "unanswered",
                        "request_user": request_user
                    })
                else:
                    return JsonResponse({"error": "Page not allowed"}, status=404)
            else:
                return JsonResponse({"error": "Method not allowed"}, status=400)

        elif user.user_type == "admin":
            Boxes = models.Boxes.objects.all()
            boxes = answered(Boxes, False)
            boxes = reversed(boxes)
            return render(request, "question_box/answer.html", {
                "boxes": boxes,
                "user": user,
                "request": request,
                "title": "unanswered",
                "request_user": request_user
            })

        else:
            return render(request, "question_box/login.html", {
                "message": "Only the administrator and therapists could have access to this page!"
            })

    if answer == "answered":
        if user.user_type == "thera":
            if request.method == "GET":

                # GET method shows the Boxes that needs to be answered
                Boxes = models.Boxes.objects.filter(answered_by=user)
                boxes = answered(Boxes, True)
                boxes = reversed(boxes)
                return render(request, "question_box/answer.html", {
                    "boxes": boxes,
                    "user": user,
                    "request": request,
                    "title": "answered",
                    "request_user": request_user
                })
            else:
                return JsonResponse({"error": "Method not allowed"}, status=400)

        elif user.user_type == "admin":
            Boxes = models.Boxes.objects.all()
            boxes = answered(Boxes, True)
            boxes = reversed(boxes)
            return render(request, "question_box/answer.html", {
                "boxes": boxes,
                "user": user,
                "request": request,
                "title": "answered",
                "request_user": request_user
            })

        else:
            return render(request, "question_box/login.html", {
                "message": "Only the administrator and therapists could have access to this page!"
            })

    elif answer == "fetch":

        # POST method gets the answer written
        if request.method == "POST":
            data = json.loads(request.body)
            if data.get("answer") is not None and data.get("box_id") is not None:
                timestamp = datetime.datetime.now()
                box = models.Boxes.objects.get(id=int(data["box_id"]))
                box.answered = True
                box.save()
                answer = models.Answers(
                    answer=data["answer"], box=box, timestamp=timestamp, confirmed=False)
                answer.save()
                return HttpResponse(status=204)
            else:
                return JsonResponse({"error": "Invalid Request."}, status=400)

        elif request.method == "PUT":
            data = json.loads(request.body)

            # Get the editted answer
            if data.get("answer_id") is not None and data.get("answer") is not None:
                answer = models.Answers.objects.get(id=data["answer_id"])
                answer.answer = data["answer"]
                answer.confirmed = False
                answer.save()
                return HttpResponse(status=204)

            # Get if the therapist chooses to omit user's edition
            elif data.get("question_id") is not None and data.get("edited") is not None:
                question = models.Questions.objects.get(id=data["question_id"])
                question.edited = data["edited"]
                question.save()
                return HttpResponse(status=204)

            else:
                return JsonResponse({"error": "Invalid Request"}, status=400)

        else:
            return JsonResponse({"error": "Method not allowed"}, status=400)

    else:
        return HttpResponse(status=404)


@login_required(login_url="/login")
@csrf_exempt
def confirm(request, username, confirm):
    request_user = models.NewUser.objects.get(username=request.user.username)
    user = models.NewUser.objects.get(username=username)

    if confirm == "confirmed":
        if user.user_type == "thera":
            if request.method == "GET":

                if request_user.username == user.username or request_user.user_type == "admin":
                    # GET method shows the Boxes that needs to be confirmed
                    Boxes = models.Boxes.objects.filter(confirmed_by=user)
                    boxes = confirmed(Boxes, True)
                    boxes = reversed(boxes)
                    return render(request, "question_box/confirm.html", {
                        "boxes": boxes,
                        "user": user,
                        "request": request,
                        "title": "confirmed",
                        "request_user": request_user
                    })

                else:
                    return JsonResponse({"error": "Page not allowed"}, status=404)
            else:
                return JsonResponse({"error": "Method not allowed"}, status=400)

        elif user.user_type == "admin":
            Boxes = models.Boxes.objects.all()
            boxes = confirmed(Boxes, True)
            boxes = reversed(boxes)
            return render(request, "question_box/confirm.html", {
                "boxes": boxes,
                "user": user,
                "request": request,
                "title": "confirmed",
                "request_user": request_user
            })

        else:
            return render(request, "question_box/login.html", {
                "message": "Only the administrator could have access to this page!"
            })

    elif confirm == "unconfirmed":
        if user.user_type == "thera":

            if request.method == "GET":

                # GET method shows the Boxes that needs to be confirmed
                Boxes = models.Boxes.objects.filter(confirmed_by=user)
                boxes = confirmed(Boxes, False)
                boxes = reversed(boxes)
                return render(request, "question_box/confirm.html", {
                    "boxes": boxes,
                    "user": user,
                    "request": request,
                    "title": "unconfirmed",
                    "request_user": request_user
                })

        elif user.user_type == "admin":
            Boxes = models.Boxes.objects.all()
            boxes = confirmed(Boxes, False)
            boxes = reversed(boxes)
            return render(request, "question_box/confirm.html", {
                "boxes": boxes,
                "user": user,
                "request": request,
                "title": "unconfirmed",
                "request_user": request_user
            })

        else:
            return render(request, "question_box/login.html", {
                "message": "Only the administrator could have access to this page!"
            })

    elif confirm == "fetch":
        if request.method == "PUT":

            # PUT method stores thera's answer
            data = json.loads(request.body)
            if data.get("answer_id") is not None:
                answer = models.Answers.objects.get(id=int(data["answer_id"]))
                answer.confirmed = data["confirmed"]
                if data["confirmed"] == False:
                    answer.post = False
                answer.save()

                return HttpResponse(status=204)
            else:
                return JsonResponse({"error": "Invalid Request."}, status=400)

        else:
            return JsonResponse({
                "error": "GET or PUT request required."
            }, status=400)

    else:
        return HttpResponse(statuc=404)


def serialize(Boxes):
    boxes = []
    for Box in Boxes:
        dic = Box.serialize()
        dic["answers"] = Box.answers.all()
        dic["questions"] = Box.questions.all()
        dic["q_a_list"] = order_by_time(dic["questions"], dic["answers"])

        # Keep track of the last element of the box
        length = len(dic["q_a_list"])
        dic["last"] = dic["q_a_list"][length-1]

        boxes.append(dic)
    return boxes


def posted(Boxes, post):
    boxes = []

    for Box in Boxes:
        dic = Box.serialize()
        dic["answers"] = []
        dic["questions"] = []
        dic["q_a_list"] = []

        # Get all questions of all the boxes without any unposted question
        if post == "Posted_Full":

            for question in Box.questions.all():

                if question.post == True:
                    dic["questions"].append(question)

            for answer in Box.answers.all():

                if answer.post == True:
                    dic["answers"].append(answer)

            if len(dic["questions"]) == len(Box.questions.all()) and len(dic["answers"]) == len(Box.answers.all()) and len(dic["questions"]) != 0:

                dic["q_a_list"] = order_by_time(
                    dic["questions"], dic["answers"])
                boxes.append(dic)

        # Get all Boxes with one or more unposted questions
        elif post == "Unposted_Full":

            for question in Box.questions.all():

                if question.post == False:
                    dic["questions"] = Box.questions.all()
                    dic["answers"] = Box.answers.all()
                    dic["q_a_list"] = order_by_time(
                        dic["questions"], dic["answers"])
                    break

            for answer in Box.answers.all():

                if answer.post == False:
                    dic["answers"] = Box.answers.all()
                    dic["questions"] = Box.questions.all()
                    dic["q_a_list"] = order_by_time(
                        dic["questions"], dic["answers"])
                    break

            if dic["questions"]:
                boxes.append(dic)

        # Get the posted questions of all the boxes without any unposted question
        elif post == "Posted_Part":

            for question in Box.questions.all():

                if question.post == True:
                    dic["questions"].append(question)

            for answer in Box.answers.all():

                if answer.post == True:
                    dic["answers"].append(answer)

            if len(dic["questions"]) != 0:
                dic["q_a_list"] = order_by_time(
                    dic["questions"], dic["answers"])
                boxes.append(dic)

    return boxes


def confirmed(Boxes, confirmed):
    boxes = []
    for Box in Boxes:
        dic = Box.serialize()
        dic["questions"] = Box.questions.all()
        dic["answers"] = []

        # Get all the confirmed answers of each Box whose answers are all confirmed
        if confirmed == True:
            for answer in Box.answers.all():
                if answer.confirmed == True:
                    dic["answers"].append(answer)
            if len(dic["answers"]) == len(Box.answers.all()) and Box.answered:
                dic["q_a_list"] = order_by_time(
                    dic["questions"], dic["answers"])
                boxes.append(dic)

        # Get all Boxes with one or more confirmed answers.(Though a box is either confirmed or unconfirmed, it wouldn't be easier to exclude the confirmed boxes)
        elif confirmed == False:
            for answer in Box.answers.all():
                if answer.confirmed == False:
                    dic["answers"] = Box.answers.all()
                    dic["q_a_list"] = order_by_time(
                        dic["questions"], dic["answers"])
                    break
            if dic["answers"] or not Box.answered:
                dic["answers"] = Box.answers.all()
                dic["q_a_list"] = order_by_time(
                    dic["questions"], dic["answers"])
                boxes.append(dic)
    return boxes


def answered(Boxes, edited):
    boxes = []
    for Box in Boxes:
        dic = Box.serialize()
        dic["answers"] = Box.answers.all()
        dic["questions"] = []

        # Get all the boxes that contain questions are editted or unanswered:
        if edited == False:
            if Box.answered == False:
                dic["questions"] = Box.questions.all()
                dic["q_a_list"] = order_by_time(
                    dic["questions"], dic["answers"])
                boxes.append(dic)

            else:
                for question in Box.questions.all():
                    if question.edited == True:
                        dic["questions"] = Box.questions.all()
                        dic["q_a_list"] = order_by_time(
                            dic["questions"], dic["answers"])
                        boxes.append(dic)
                        break

        # Get all the boxes which are answered and contains no question that is editted
        if edited == True:
            if Box.answered == True:
                for question in Box.questions.all():
                    if question.edited == False:
                        dic["questions"].append(question)
                if len(dic["questions"]) == len(Box.questions.all()):
                    dic["q_a_list"] = order_by_time(
                        dic["questions"], dic["answers"])
                    boxes.append(dic)

    return boxes


# Order the questions and answers in a box by time
def order_by_time(questions, answers):
    def get_time(obj):
        time = obj["content"].timestamp
        return time.strftime("%y") + time.strftime("%m") + time.strftime("%d") + time.strftime("%H") + time.strftime("%M") + time.strftime("%S")

    q_a_list = []

    for question in questions:
        q_a_list.append({
            'type': "question",
            'content': question
        })

    for answer in answers:
        q_a_list.append({
            'type': "answer",
            'content': answer
        })

    q_a_list.sort(key=get_time)

    return q_a_list
