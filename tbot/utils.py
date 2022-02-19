import datetime
import logging

import telegram
from telegram import Update
from telegram.ext import CallbackContext

from based.models import User, Task, Schedule, Excercise

logger = logging.getLogger('deltaplan')


def log_errors(f):
    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as err:
            logger.debug(f'bot running err: {err}')
            raise err

    return inner


def get_kbk(exc):
    button = telegram.InlineKeyboardButton
    keyboard = [
        button("Редактировать", callback_data=f"edit_{exc}"),
        button("! Удалить !", callback_data=f"delete_{exc}")]
    reply_markup = telegram.InlineKeyboardMarkup([keyboard])
    return reply_markup


@log_errors
def start(update: Update, context: CallbackContext):
    userid = update.message.chat_id
    from_user = update.message.from_user
    uname = from_user.username if from_user.username else ''
    fname = from_user.first_name if from_user.first_name else ''
    lname = from_user.last_name if from_user.last_name else ''
    flname = f'{fname} {lname}'.lstrip().rstrip()[:42]

    text = ''
    if not User.objects.filter(userid=userid).first():
        User(userid=userid, name=flname, nick=uname, userstate=0,
             timezone=3, sleepstart="22:00", sleepend="10:00").save()
    else:
        text += 'И снова здравствуйте!\n'

    u = User.objects.get(userid=userid)
    text += "Добро пожаловать на дельтаплан!\n\n"
    text += f"Ваши настройки:\nЧасовой пояс: GMT+{u.timezone}\nТихое время: {u.sleepstart} — {u.sleepend}\n\n"
    text += "Добавить задачу /add \nСписок задач /list \nРасписание /sched\nИзменить настройки /sets"
    update.message.reply_text(text)


def do_callback(update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    message = query.message
    button = query.data
    strips = button.split("_")

    if len(strips) > 1:
        button = strips[0]
        chosen = 0
        try:
            chosen = int(strips[1])
        except Exception as err:
            print("pasrse as int err", err)

        if button == 'snooze':
            snooze_exc(message, chosen)
        elif button == 'done':
            done_exc(message, chosen)
        elif button == 'edit':
            go_task(query, context, taskid=chosen, is_started=True)
        elif button == 'delete':
            delete_exc(message, context.bot, chosen)


@log_errors
def add_task(update: Update, context: CallbackContext):
    go_task(update, context, taskid=0, is_started=True)


@log_errors
def go_task(update: Update, context: CallbackContext, taskid=0, is_started=False):
    """
    is_started = True передаётся в двух случаях: с комманды /add, и тогда taskid=0
                        или с кнопки edit, и тогда передаётся также id задачи
    Далее с каждой итерацией увеличивается переменная состояния, текущий шаг.
    Если состояние равно 0, но is_started не передан, значит это случайный ввод.
    Кроме state, текущего шага, в User сохраняется taskstate, id текущей задачи.
    В задаче Task сохраняется флаг status. Он пригодится для временного отключения.
    На этапе создания статус задачи = -1. По завершению устанавливается равным 1.
    Пока есть задача со статусом -1, т.е. не законченная, новая не создаётся.
    """
    userid = update.message.chat_id
    messg = update.message.text
    u = User.objects.get(userid=userid)
    state = u.userstate

    if is_started:
        if taskid:
            t = Task.objects.get(userid=u, id=taskid)
            u.taskstate = taskid
            update.message.edit_text(f"Редактирование {t.taskname}\n{t.counts} {t.measure}"
                                     f" каждые {sec_to_human(t.repper)} начало {t.notitime}")
            update.message.reply_text('Введите название:')
        else:
            update.message.reply_text("Добавление новой задачи. Название:")
            t = Task.objects.filter(userid=u, status=-1).first()
            if not t:
                t = Task(userid=u, status=-1)
                t.save()
            u.taskstate = t.id
        u.userstate = 1
        u.save()
        return

    if state == 0:
        update.message.reply_text("Чтобы добавить задачу, нажмите /add")
        return

    taskstate = u.taskstate
    t = Task.objects.get(userid=u, id=taskstate)

    if state == 1:
        t.taskname = messg
        t.save()
        update.message.reply_text("Количество (N) (повторений / единиц):")

    elif state == 2:
        strips = messg.split()
        try:
            counts = int(strips[0])
        except Exception as err:
            print(err)
            update.message.reply_text("Введите через пробел число и измерение\n"
                                      "Например, 5 повторов или 10 страниц или 3 р")
            return
        t.counts = counts
        t.measure = strips[1] if len(strips) > 1 else 'ед.'
        t.save()
        update.message.reply_text("Периодичность задачи (N) (д / ч / м / мин)")

    elif state == 3:
        strips = messg.split()
        try:
            if len(strips) > 1:
                multplier = strips[1]
                multplr_dict = {'д': 23 * 60 * 60, 'ч': 60 * 60, 'м': 60, 'мин': 60}
                if multplier in multplr_dict.keys():
                    mutiply = multplr_dict[multplier]
                else:
                    mutiply = 60
            else:
                mutiply = 60
            t.repper = int(strips[0]) * mutiply
            t.save()
            update.message.reply_text("Время (начала) уведомлений:")
        except Exception as err:
            print(err)
            update.message.reply_text("Введите через пробел число и значение\n"
                                      "Например, 3 ч или 2 д или 90 мин")
            return

    elif state == 4:
        nowtime = datetime.datetime.now().timestamp()
        nowmins = datetime.datetime.now().strftime("%H:%M")
        now_hminsec = datetime.datetime.strptime(nowmins, "%H:%M").timestamp()
        try:
            inp_hminsec = datetime.datetime.strptime(messg, "%H:%M").timestamp()
        except Exception as err:
            print(err)
            update.message.reply_text("Введите время в формате ЧЧ:ММ\nНапример, 12:30")
            return
        delta = inp_hminsec - now_hminsec - u.timezone * 60 * 60
        if delta < 0:
            delta += 60 * 60 * 24
        notitime = int(nowtime + delta)
        t.notitime = messg
        t.notinext = notitime
        t.status = 1
        t.save()
        old_sch = Schedule.objects.filter(userid=u, taskid=t).first()
        if old_sch:
            old_sch.delete()
        sc = Schedule(userid=u, taskid=t, notitime=notitime, multiply=0)
        sc.save()
        u.taskstate = 0
        delta_hum = sec_to_human(delta)
        update.message.reply_text(f"Окей, следущее срабатывание через {delta_hum}")

    state = state + 1 if state < 4 else 0
    u.userstate = state
    u.save()


@log_errors
def show_list(update: Update, context: CallbackContext):
    userid = update.message.chat_id
    tasks = Task.objects.filter(userid=User.objects.get(userid=userid), status__gt=-1)
    if tasks.count():
        text = "Список задач:\n"
        for indx, tsk in enumerate(tasks):
            text += f"{indx + 1}. {tsk.taskname}\n"
        text += "\nДля выбора введите номер\n"
    else:
        text = "Список пуст\n"
    text += "Добавить задачу /add\nРасписание /sched"
    update.message.reply_text(text)


@log_errors
def sec_to_human(sec):
    sec = int(sec)
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    res = f"{m}м" if m else ''
    if h > 0:
        res = f"{h}ч " + res
    if d > 0:
        res = f"{d}д " + res
    return res


@log_errors
def details_task(update: Update, context: CallbackContext):
    userid = update.message.chat_id
    taskid = int(update.message.text) - 1
    tasks = Task.objects.filter(userid=User.objects.get(userid=userid), status__gt=-1)
    if 0 <= taskid <= tasks.count():
        # TODO придумать что-нибудь получше
        tsk = tasks[taskid]
        sec = tsk.repper if tsk.repper else 0
        res = sec_to_human(sec)
        text = f"<{tsk.taskname}> {tsk.counts} {tsk.measure} повтор каждые {res}"
        update.message.reply_text(text, reply_markup=get_kbk(tsk.id))
    else:
        update.message.reply_text('Числа используются для выбора задачи.\n'
                                  f'Задачи №{taskid + 1} не существует.\nСписок /list')


@log_errors
def snooze_exc(message, taskid):
    sch = Schedule.objects.get(taskid=Task.objects.get(id=taskid))
    sch.notitime = sch.notitime + 30 * 60
    sch.save()
    message.edit_text(f"<{sch.taskid.taskname}> Отложено на полчаса")


@log_errors
def delete_exc(message, bot, taskid):
    t = Task.objects.get(id=taskid)
    s = Schedule.objects.filter(taskid=t).last()
    if s:
        userid = message.chat_id
        if s.mess_id:
            bot.delete_message(chat_id=userid, message_id=s.mess_id)
        s.delete()
    t.delete()
    message.edit_text(f"<{t.taskname}> удалена")


@log_errors
def done_exc(message, taskid):
    taskindx = int(taskid)
    tsk = Task.objects.get(id=taskindx)
    sch = Schedule.objects.get(taskid=tsk)
    text = f"{tsk.taskname} {tsk.counts * int(sch.multiply)} {tsk.measure}"
    sch.delete()
    nowtime = int(datetime.datetime.now().timestamp())
    exc = Excercise(userid=tsk.userid, taskid=tsk, tfinish=nowtime, human=text)
    exc.save()
    message.edit_text(text=f"☑️ {text}")


@log_errors
def force_dnd(update, context):
    userid = update.message.chat_id
    timenow = datetime.datetime.now().timestamp()
    postpone_time = timenow + 60 * 60
    u = User.objects.get(userid=userid)
    u.userstate = 7
    u.save()
    sch = Schedule.objects.filter(userid=u, notitime__lt=postpone_time)
    for s in sch:
        s.notitime = postpone_time
        s.save()
        try:
            context.bot.edit_message_text(f"<{s.taskid.taskname}> отложено на час", userid, s.mess_id)
        except Exception as err:
            print(err)
    update.message.reply_text("Ок, тихий час!")


@log_errors
def set_tings(update, context):
    update.message.reply_text("В разработке")


@log_errors
def get_sched(update, context):
    update.message.reply_text("Cкоро!")
