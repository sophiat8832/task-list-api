from flask import Blueprint, jsonify, abort, make_response, request
from app.models.task import Task
from app.models.goal import Goal
from app import db
from datetime import datetime
import os, requests


tasks_bp = Blueprint("tasks_bp", __name__, url_prefix="/tasks")
goals_bp = Blueprint("goals_bp", __name__, url_prefix="/goals")


def validate_item_by_id(model, id):
    try:
        id = int(id)
    except:
        abort(make_response({"message":f"{model.__name__} {id} invalid"}, 400))

    item = model.query.get(id)

    return item if item else abort(make_response({"message":f"{model.__name__} {id} not found"}, 404))


@tasks_bp.route("", methods=["POST"])
def create_task():
    request_body = request.get_json()

    if "title" not in request_body or "description" not in request_body:
        abort(make_response({"details":"Invalid data"}, 400))

    new_task = Task(title=request_body["title"],
                    description=request_body["description"])
    
    db.session.add(new_task)
    db.session.commit()

    return {"task": new_task.to_dict()}, 201


@tasks_bp.route("", methods=["GET"])
def get_all_tasks():
    query = request.args.get("sort")

    if query == "asc":
        tasks = Task.query.order_by(Task.title.asc())
    elif query == "desc":
        tasks = Task.query.order_by(Task.title.desc())
    else:
        tasks = Task.query.all()

    tasks_response = [task.to_dict() for task in tasks]
    return jsonify(tasks_response)


@tasks_bp.route("/<id>", methods=["GET"])
def get_one_task(id):
    task = validate_item_by_id(Task, id)
    return {"task": task.to_dict()}, 200


@tasks_bp.route("/<id>", methods=["PUT"])
def update_task(id):
    task = validate_item_by_id(Task, id)

    request_body = request.get_json()
    task.title = request_body["title"]
    task.description = request_body["description"]
    
    db.session.commit()
    return {"task": task.to_dict()}, 200


@tasks_bp.route("/<id>", methods=["DELETE"])
def delete_task(id):
    task = validate_item_by_id(Task, id)

    db.session.delete(task)
    db.session.commit()

    return {
        "details": f"Task {id} \"{task.title}\" successfully deleted"
    }, 200


@tasks_bp.route("/<id>/mark_complete", methods=["PATCH"])
def mark_complete(id):
    task = validate_item_by_id(Task, id)

    task.completed_at = datetime.utcnow()

    url = "https://slack.com/api/chat.postMessage"
    slack_token = os.environ.get('SLACKBOT_TOKEN')
    header = {"Authorization": f"Bearer {slack_token}"}
    data = {
        "channel": "task-notifications",
        "text": f"Someone just completed the task {task.title}"
        }
    
    requests.post(url, data=data, headers=header)

    db.session.commit()

    return {"task": task.to_dict()}, 200


@tasks_bp.route("/<id>/mark_incomplete", methods=["PATCH"])
def mark_incomplete(id):
    task = validate_item_by_id(Task, id)

    task.completed_at = None

    db.session.commit()
    return {"task": task.to_dict()}, 200


@goals_bp.route("", methods=["POST"])
def create_goal():
    request_body = request.get_json()

    if "title" not in request_body:
        abort(make_response({"details":"Invalid data"}, 400))

    new_goal = Goal(title=request_body["title"])
    
    db.session.add(new_goal)
    db.session.commit()

    return {"goal": new_goal.to_dict()}, 201


@goals_bp.route("", methods=["GET"])
def get_all_goals():
    goals = Goal.query.all()
    goals_response = [goal.to_dict() for goal in goals]
    return jsonify(goals_response)


@goals_bp.route("/<goal_id>", methods=["GET"])
def get_one_goal(goal_id):
    goal = validate_item_by_id(Goal, goal_id)
    return {"goal": goal.to_dict()}, 200


@goals_bp.route("/<goal_id>", methods=["PUT"])
def update_goal(goal_id):
    goal = validate_item_by_id(Goal, goal_id)

    request_body = request.get_json()
    goal.title = request_body["title"]
    
    db.session.commit()
    return {"goal": goal.to_dict()}, 200


@goals_bp.route("/<goal_id>", methods=["DELETE"])
def delete_goal(goal_id):
    goal = validate_item_by_id(Goal, goal_id)

    db.session.delete(goal)
    db.session.commit()

    return {
        "details": f"Goal {goal_id} \"{goal.title}\" successfully deleted"
    }, 200


@goals_bp.route("/<goal_id>/tasks", methods=["POST"])
def send_tasks_to_goal(goal_id):
    goal = validate_item_by_id(Goal, goal_id)

    request_body = request.get_json()

    tasks = Task.query.all()

    task_ids = request_body["task_ids"]

    for task in tasks:
        if task.id in task_ids:
            task.goal_id = goal.goal_id
    
    db.session.commit()
    return {"id": goal.goal_id, "task_ids": task_ids}, 200


@goals_bp.route("/<goal_id>/tasks", methods=["GET"])
def get_tasks_of_one_goal(goal_id):
    goal = validate_item_by_id(Goal, goal_id)
    tasks = Task.query.all()
    
    tasks_response = [task.to_dict() for task in tasks if task.goal_id == goal.goal_id]
    
    return {
        "id": goal.goal_id,
        "title": goal.title,
        "tasks": tasks_response
        }