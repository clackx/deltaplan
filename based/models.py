from django.db import models


class User(models.Model):
    userid = models.IntegerField(default=0)
    name = models.CharField(max_length=40)
    nick = models.CharField(max_length=40, null=True)
    userstate = models.IntegerField(default=0)
    taskstate = models.IntegerField(default=0)
    timezone = models.IntegerField(default=0)
    sleepstart = models.CharField(max_length=5)
    sleepend = models.CharField(max_length=5)

    def __str__(self):
        return f"id{self.id} {self.name[:20]} @{self.nick}"


class Task(models.Model):
    userid = models.ForeignKey(User, on_delete=models.CASCADE)
    taskname = models.CharField(max_length=200)
    counts = models.IntegerField(default=0)
    measure = models.CharField(max_length=20)
    repper = models.IntegerField(default=0)
    notitime = models.CharField(max_length=5)
    notinext = models.IntegerField(default=0)
    status = models.IntegerField(default=0)

    def __str__(self):
        return f"id{self.id} {self.taskname}"


class Schedule(models.Model):
    taskid = models.ForeignKey(Task, on_delete=models.CASCADE)
    userid = models.ForeignKey(User, on_delete=models.CASCADE)
    notitime = models.IntegerField(default=0)
    multiply = models.IntegerField(default=0)
    mess_id = models.IntegerField(default=0)


class Excercise(models.Model):
    userid = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    taskid = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True)
    tstart = models.IntegerField(default=0)
    tfinish = models.IntegerField(default=0)
    human = models.CharField(max_length=200)
