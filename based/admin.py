from datetime import datetime

from django.contrib import admin

from based.models import User, Task, Schedule, Excercise


def sec_to_hum(sec):
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    res = ''
    res = f"{s}сек" + res if s > 0 else res
    res = f"{m}мин " + res if m > 0 else res
    res = f"{h}ч " + res if h > 0 else res
    res = f"{d}д " + res if d > 0 else res
    return res


@admin.register(User)
class UsersAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'nick', 'timezone', 'sleepstart', 'sleepend', 'userstate')


@admin.register(Task)
class TasksAdmin(admin.ModelAdmin):
    list_display = ('id', 'userid', 'taskname', 'repeats', 'period', 'notitime', 'notinext', 'htime', 'status')

    def htime(self, obj):
        return datetime.fromtimestamp(obj.notinext + 3 * 60 * 60).strftime("%d.%m %H:%M")

    def repeats(self, obj):
        return f"{obj.counts} {obj.measure}"

    def period(self, obj):
        sec = obj.repper
        return sec_to_hum(sec)


@admin.register(Schedule)
class SchedulAdmin(admin.ModelAdmin):
    list_display = ('id', 'taskid', 'userid', 'notitime', 'htime', 'remtime', 'multiply')

    def htime(self, obj):
        return datetime.fromtimestamp(obj.notitime + 3 * 60 * 60).strftime("%d.%m %H:%M")

    def remtime(self, obj):
        sec = (datetime.fromtimestamp(obj.notitime) - datetime.now()).total_seconds()
        return sec_to_hum(int(sec))


@admin.register(Excercise)
class ExcerciseAdmin(admin.ModelAdmin):
    list_display = ('id', 'taskid', 'userid', 'tfinish', 'htime', 'human')

    def htime(self, obj):
        return datetime.fromtimestamp(obj.tfinish + 3 * 60 * 60).strftime("%d.%m %H:%M")
