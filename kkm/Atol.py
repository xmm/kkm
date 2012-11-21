# -*- coding: utf-8 -*-
'''
 Copyright (c) 2005, 2012
 @author: Marat Khayrullin <xmm.dev@gmail.com>
'''

'''
 Использованные документы:
 <1>: Атол технологии
       Руководство программиста: Протокол работы ККМ v2.4
 <2>: Атол технологии
       Руководство программиста: Общий драйвер ККМ v.5.1
       (версия док-ции: 1.7 от 15.05.2002)
 <3>: Курское ОАО "Счетмаш"
       Инструкция по программированию РЮИБ.466453.528 И15
       Машина электронная контрольно-кассовая Феликс-Р Ф
<4>: Атол технологии
       Приложение к протоколу работы ККМ (2009)
'''

import kkm
from transCoding import cp866 as codeset
from Exceptions import *

from decimal import Decimal
import string
import time
import logging
logger = logging.getLogger('kkm')

_atol_STX = '\x02'  # ^B Начало текста
_atol_ETX = '\x03'  # ^C Конец текста
_atol_EOT = '\x04'  # ^D Конец передачи
_atol_ENQ = '\x05'  # ^E Запрос
_atol_ACK = '\x06'  # ^F Подтверждение
_atol_DLE = '\x10'  # ^Q Экранирование управ. символов
_atol_NAK = '\x15'  # ^U Отрицание
_atol_FS  = '\x1C'  # ^] Разделитель полей

_atol_CON_attempt  = 20   # Кол-во
_atol_ANS_attempt  = 20   # Кол-во
_atol_ENQ_attempt  = 5    # Кол-во проверок готовности ККМ
_atol_ACK_attempt  = 10
_atol_ACK_timeout  = 5    # Время ожидания между проверками готовности ККМ
_atol_DLE_timeout  = 1    # Время ожидания ответа на DLE запрос (тек. статус)
_atol_T1_timeout   = 5    # ?Стандартное время ожидания получения 1го байта
_atol_T2_timeout   = 200  # Время ожидания состояния "Идет передача ответа"
_atol_T3_timeout   = 5
_atol_T4_timeout   = 5
_atol_T5_timeout   = 200  # Время ожидания состояния "Готов к передаче ответа"
_atol_T6_timeout   = 5
_atol_DAT_timeout  = 5
_atol_STX_attempt  = 100  # Кол-во попыток прочитать STX байт

_atol_PASSWD_len   = 4      # Длина пароля
_atol_ANSWER_len   = 10240  # Max длина ответа от ККМ

# Коды комманд
_atol_GetLastSummary_cmd  = 'X'
_atol_GetStatus_cmd       = '?'
_atol_GetCurrentState_cmd = 'E'
_atol_GetTypeDevice_cmd   = '\xA5'
_atol_SetMode_cmd         = 'V'
_atol_ResetMode_cmd       = 'H'
_atol_PrintString_cmd     = 'L'
_atol_PrintToDisplay_cmd  = '\x8F'
_atol_OpenCashBox_cmd     = '\x80'
_atol_CashIncom_cmd       = 'I'
_atol_CashOutcom_cmd      = 'O'
_atol_OpenCheck_cmd       = '\x92'
_atol_Sell_cmd            = 'R'
_atol_Return_cmd          = 'W'
_atol_Discount_cmd        = 'C'
_atol_Annulate_cmd        = 'Y'
_atol_Payment_cmd         = 'J'
_atol_XReport_cmd         = 'g'
_atol_ClearingReport_cmd  = 'T'
_atol_ZReport_cmd         = 'Z'
_atol_CommonClear_cmd     = 'w'
_atol_ReadTable_cmd       = 'F'
_atol_Programming_cmd     = 'P'
_atol_ZReportToMem_cmd    = '\xB4'
_atol_ZReportFromMem_cmd  = '\xB5'

_atol_Select_mode         = 0
_atol_Registration_mode   = 1
_atol_XReport_mode        = 2
_atol_ZReport_mode        = 3
_atol_Programming_mode    = 4
_atol_Inspector_mode      = 5

# Битовые значения переменной flags (<1>стр.34)
_atol_TestOnly_flag      = 0x01
_atol_CheckCash_flag     = 0x02

### Коды режима отчетов без гашения
_atol_X_report          = 1
_atol_Department_report = 2
_atol_Cashier_report    = 3
_atol_Goods_report      = 4
_atol_Hour_report       = 5
_atol_Quantity_report   = 7

_atol_Report_timeout    = 0.5

# Тип закрытия чека (<1>стр.38)
_atol_cash_payment  = 1  # наличными
_atol_type2_payment = 2  # кредитом
_atol_type3_payment = 3  # тарой
_atol_type4_payment = 4  # пл. картой

# Параметры ККМ различных моделей
# type.model: (name, type, model, majorver, minorver, build,
#              maxstring, klishelen, klishemax)
_modelTable = {
    '1.14': (u'Феликс-Р Ф', 1, 14, 2, 3, 2185, 20, 20, 8),
    '1.24': (u'Феликс-Р К', 1, 24, 2, 4, 3700, 38, 38, 8),
    '1.41': (u'PayVKP-80K', 1, 24, 2, 4, 3700, 42, 42, 8),
    }
_atol_StringMax_idx = 6
_atol_KlisheLen_idx = 7
_atol_KlisheMax_idx = 8

exceptionTable = {
    1: KKMCommonErr(u'Контрольная лента обработана без ошибок.'),
    8: KKMWrongMoneyErr,
    10: KKMWrongQuantityErr,
    15: KKMCommonErr(u'Повторная скидка на операцию не возможна'),
    20: KKMCommonErr(u'Неверная длина'),
    26: KKMCommonErr(u'Отчет с гашением прерван. Вход в режим заблокирован'),
    30: KKMCommonErr(u'Вход в режим заблокирован'),
    102: KKMIncorectModeErr,
    103: KKMOutOfPaperErr,
    106: KKMCommonErr(u'Неверный тип чека'),
    114: KKMCommonErr(u'Сумма платежей меньше суммы чека'),
    117: KKMCommonErr(u'Переполнение суммы платежей'),
    122: KKMCommonErr(u'Данная модель ККМ не может выполнить команду'),
    123: KKMCommonErr(u'Неверная величина скидки / надбавки'),
    127: KKMCommonErr(u'Переполнение при умножении'),
    134: KKMLowPaymentErr,
    136: KKMNeedZReportErr,
    140: KKMCommonErr(u'Неверный пароль'),
    143: KKMCommonErr(u'Обнуленная касса (повторное гашение не возможно)'),
    151: KKMCommonErr(u'Подсчет суммы сдачи не возможен'),
    154: KKMCommonErr(u'Чек закрыт - операция невозможна'),
    155: KKMCommonErr(u'Чек открыт - операция невозможна'),
    156: KKMCommonErr(u'Смена открыта - операция невозможна'),
    190: KKMCommonErr(u'Необходимо провести профилактические работы'),
    201: KKMCommonErr(u'Нет связи с внешним устройством'),
    209: KKMCommonErr(u'Перегрев головки принтера'),
    210: KKMCommonErr(u'Ошибка обмена с ЭКЛЗ на уровне интерфейса I2O')
}


def checkException(ans):
    try:
        if (ans[0] != 'U'):
            logger.error(str(KKMUnknownAnswerErr))
            raise KKMUnknownAnswerErr
        else:
            raiseException(ord(ans[1]))
            return ans
    except IndexError:
        logger.error(str(KKMUnknownAnswerErr))
        raise KKMUnknownAnswerErr


def raiseException(code):
    if (code != 0):
        try:
            logger.error(unicode(exceptionTable[code]))
            raise exceptionTable[code]
        except KeyError:
            logger.error(unicode(KKMUnknownErr(u'Неизвестный код ошибки: %d' % code)))
            raise KKMUnknownErr(u'Неизвестный код ошибки: %d' % code)


def _escaping(data):
    replace = string. replace
    escaped = replace(data, _atol_DLE, _atol_DLE + _atol_DLE)
    return replace(escaped, _atol_ETX, _atol_DLE + _atol_ETX)


def _unescaping(data):
    replace = string.replace
    unescaped = replace(data, _atol_DLE + _atol_ETX, _atol_ETX)
    unescaped = replace(unescaped, _atol_DLE + _atol_DLE, _atol_DLE)
    return unescaped


def _calc_crc(data):
    #from binascii import crc32
    #return crc32(data)
    crc = 0
    for i in range(len(data)):
        crc ^= ord(data[i])
    return crc

#def createAtol( device, speed, password ):
#    return AtolKKM( device, speed, password )


class AtolKKM(kkm.KKM):
    """Драйвер к ККМ с протоколом обмена компании 'Атол технологии'(версии. 2.4)
    """

    def __init__(self, device, password):
        _passwordLen       = 4           # Длина пароля
        _moneyWidth        = 10          # Кол-во разрядов
        _quantityWidth     = 10          # Кол-во разрядов
        _stringMax         = 20          # Максимальное значение
        _displayMax        = 20          # Максимальная длина строки для вывода на дисплей пользователя
        _moneyMax          = 9999999999  # Максимальное значение
        _quantityMax       = 9999999999  # Максимальное значение
        _moneyPrecision    = 100         # Точность денежной единицы после десят. точки (в виде множителя)
        _quantityPrecision = 1000        # Точность единицы измерения веса после десят. точки (в виде множителя)

        self.__flags       = _atol_CheckCash_flag  # Флаги режима регистрации
        self._kkmPassword = self.number2atol(password, 4)
        kkm.KKM.__init__(self, device, self._kkmPassword)
        typeDev = self.GetTypeDevice()
        self.model = model = str(ord(typeDev['type'])) + '.' + str(ord(typeDev['model']))
        if model not in _modelTable:
            raise KKMUnknownModelErr
        self.initStringMax()
        self.initKlisheMax()
        self.initKlisheLen()

    def OpenDevice(self):
        import serial
        # Проверить наличие блокировки устройства
        # Заблокировать или вывалиться с ошибкой
        try:
            self._kkm = serial.Serial(**self._device)
        except:
            raise KKMCommonErr(u'System error at opening KKM device')
        if (not self._kkm):
            raise KKMCommonErr(u'Unknown error at opening KKM device')

    def _set_readtimeout(self, timeout):
        self._kkm.setTimeout(timeout)

    def _atol_send_data(self, data):
        kkm = self._kkm

        logger.debug('data: %s len: %d', data, len(data))
        data = _escaping(data) + _atol_ETX
        crc = _calc_crc(data)
        data = _atol_STX + data + chr(crc)   # Есть ли у Феликса max длина буфера?
        logger.debug('escaped data: %s len: %d crc: %d', data, len(data), crc)

        try:
            ### Активный передатчик #######################
            for i in range(_atol_CON_attempt):
                for j in range(_atol_ENQ_attempt):
                    kkm.write(_atol_ENQ)
                    self._set_readtimeout(_atol_T1_timeout)
                    ch = kkm.read(1)
                    if (ch == _atol_NAK):
                        time.sleep(_atol_T1_timeout * 0.1)  # Перевести в секунды
                    elif (ch == _atol_ENQ):
                        time.sleep(_atol_T1_timeout * 0.1)  # Перевести в секунды
                        break
                    elif (ch == ''):
                        continue
                    elif (ch == _atol_ACK):
                        for k in range(_atol_ACK_attempt):
                            kkm.write(data)
                            self._set_readtimeout(_atol_T3_timeout)
                            ch = kkm.read(1)
                            #print "2[%s]" %(ch)
                            if (ch == ''):
                                time.sleep(0.5)
                                continue
                            elif (ch != _atol_ACK or (ch == _atol_ENQ and k == 1)):
                                continue
                            elif (ch == _atol_ACK or (ch == _atol_ENQ and k > 1)):
                                if (ch == _atol_ACK):
                                    kkm.write(_atol_EOT)
                                ### Активный приемник #######################
                                if (ch == _atol_ACK):
                                    for unused in range(_atol_ANS_attempt):
                                        self._set_readtimeout(_atol_T5_timeout)
                                        ch = kkm.read(1)
                                        #print "3[%s]" %(ch)
                                        if (ch == ''):
                                            logger.error(str(KKMNoAnswerErr))
                                            raise KKMNoAnswerErr
                                        elif (ch == _atol_ENQ):
                                            break
                                ch = ''
                                for unused in range(_atol_ACK_attempt):
                                    kkm.write(_atol_ACK)
                                    for unused in range(_atol_ANS_attempt):
                                        if (ch != _atol_STX):
                                            self._set_readtimeout(_atol_T2_timeout)
                                            ch = kkm.read(1)
                                            #print "4[%s]" %(ch)
                                        if (ch == ''):
                                            logger.error(str(KKMNoAnswerErr))
                                            raise KKMNoAnswerErr
                                        elif (ch == _atol_ENQ):
                                            break
                                        elif (ch == _atol_STX):
                                            answer = ''
                                            DLE_Flag = 0
                                            while (1 == 1):  # Длину буфера проверять не надо
                                                self._set_readtimeout(_atol_T6_timeout)
                                                ch = kkm.read(1)
                                                #print "5[%s]" %(ch)
                                                if (ch == ''):
                                                    break
                                                else:
                                                    if (DLE_Flag == 1):
                                                        #print "DLE off"
                                                        DLE_Flag = 0
                                                    else:
                                                        if (ch == _atol_ETX):  # Не экранир-ый ETX
                                                            #print "ETX"
                                                            break
                                                        elif (ch == _atol_DLE):
                                                            #print "DLE on"
                                                            DLE_Flag = 1
                                                answer = answer + ch
                                            # self._set_readtimeout(kkm, _atol_T6_timeout) # Уже установлен
                                            ch = kkm.read(1)  # Ждем CRC
                                            #print "6[%s]" %(ch)
                                            if (ch == ''):
                                                break
                                            #print "len=%d" %(len(answer))
                                            #for v in range(len(answer)):
                                            #    print ":%d" %(ord(answer[v]))
                                            crc = _calc_crc(answer + _atol_ETX)
                                            #print "ans:[%s] crc:[%d] ?= [%d]" %(answer + _atol_ETX,crc,ord(ch))
                                            if (crc != ord(ch)):
                                                #print "CRC err"
                                                kkm.write(_atol_NAK)
                                                break
                                            else:
                                                kkm.write(_atol_ACK)
                                                self._set_readtimeout(_atol_T4_timeout)
                                                ch = kkm.read(1)
                                                #print "7[%s]" %(ch)
                                                if (ch == _atol_EOT or ch == ''):
                                                    #print "answer1:" + answer
                                                    return _unescaping(answer)
                                                elif (ch == _atol_STX):
                                                    continue
                                                else:
                                                    self._set_readtimeout(2)  # _atol_T???_timeout
                                                    ch = kkm.read(1)
                                                    #print "8[%s]" %(ch)
                                                    if (ch == ''):
                                                        #print "answer2:" + answer
                                                        return _unescaping(answer)
                                                    else:
                                                        break
                                        else:
                                            continue
                                kkm.write(_atol_EOT)
                                logger.error(str(KKMNoAnswerErr))
                                raise KKMNoAnswerErr
                        kkm.write(_atol_EOT)
                        logger.error(str(KKMConnectionErr))
                        raise KKMConnectionErr
                    else:
                        break
            kkm.write(_atol_EOT)
        except OSError:  # for Linux
            import sys
            exc = sys.exc_info()
            if exc[1].errno == 19:
                logger.error(str(KKMNoDeviceErr))
                raise KKMNoDeviceErr
            else:
                logger.error(str(KKMConnectionErr))
                raise KKMConnectionErr
        except Exception:  # win32file raise common exception, not OSError as Linux
            logger.error(str(KKMConnectionErr))
            raise KKMConnectionErr
        logger.error(str(KKMConnectionErr))
        raise KKMConnectionErr

    def str2atol(self, txt, length):
        """Преобразование строки в формат ккм.

        C локализацией и дополнением пробелами до значения length.
        """
        txt = unicode(txt).encode('cp866')
        ctrlNum = 0
        for c in txt:
            if c < ' ':
                ctrlNum += 1
        length += ctrlNum
        if (len(txt) < length):
            txt = string.ljust(txt, length)
        return txt[:length]

    def atol2str(self, txt):
        """Преобразование строки из формата ккм (локализация)."""
        return txt.decode('cp866')

    def number2atol(self, number, width=2):
        """Преобразование числа в формат ккм.

        Если width > длины number - дополнить слева нулями,
        иначе срезать конец.
        Ширина в знаках, а не в байтах!!!
        <1>стр.17 Запихать по 2 цифры в один байт."""
        number = str(number)
        if ((width % 2) != 0):
            width += 1
        if (len(number) >= width):
            number = number[:width]
        else:
            number = string.zfill(str(number), width)
        val = ''
        i = 0
        while (i < len(number)):
            val = val + chr(int(number[i]) << 4 | int(number[i + 1]))
            i += 2
        return val

    def atol2number(self, number):
        """Преобразование числа из формата ккм.

        <1>стр.17"""
        val = ''
        i = 0
        for i in range(len(number)):
            dec = ord(number[i])
            if (dec < 10):
                zero = '0'
            else:
                zero = ''
            val = val + zero + hex(dec)[2:]
        return long(val)

    def money2atol(self, money, width=None):
        """Преобразование денежной суммы (decimal) в формат ккм (МДЕ).

        ширина в знаках, а не в байтах!!!
        <1>стр.17"""
        if (width == None):
            width = self._moneyWidth
        elif (width > self._moneyWidth):
            logger.error(str(KKMWrongMoneyErr(u'Затребована ширина превышающая максимально допустимое значение')))
            raise KKMWrongMoneyErr(u'Затребована ширина превышающая максимально допустимое значение')
        money = round(money * self._moneyPrecision)
        if (money > self._moneyMax):
            logger.error(str(KKMWrongMoneyErr(u'Число типа "money" превышает максимально допустимое значение')))
            raise KKMWrongMoneyErr(u'Число типа "money" превышает максимально допустимое значение')
        return self.number2atol(long(money), width)

    def atol2money(self, money):
        """Преобразование из формата ккм (МДЕ) в денежную сумму (decimal).

        <1>стр.17"""
        return Decimal(self.atol2number(money)) / self._moneyPrecision

    def quantity2atol(self, quantity, width=None):
        """Преобразование количества в формат ккм.

        ширина в знаках, а не в байтах!!!
        <1>стр.17"""
        if (width == None):
            width = self._quantityWidth
        elif (width > self._quantityWidth):
            logger.error(str(KKMWrongQuantityErr(u'Затребована ширина превышающая максимально допустимое значение')))
            raise KKMWrongQuantityErr(u'Затребована ширина превышающая максимально допустимое значение')
        quantity = round(quantity * self._quantityPrecision)  # Марсель! Округлять или срезать ???
        if (quantity > self._quantityMax):
            logger.error(str(KKMWrongQuantityErr(u'Число типа "quantity" превышает максимально допустимое значение')))
            raise KKMWrongQuantityErr(u'Число типа "quantity" превышает максимально допустимое значение')
        quantity = str(quantity)
        dot = string.find(quantity, '.')
        if (dot > 0):
            quantity = quantity[0:dot]
        else:
            logger.critical(str(RuntimeError(u'Невозможное значение')))
            raise RuntimeError(u'Невозможное значение')
        # Для скорости можно сдублировать, иначе - лишнее двойное преобразование
        return self.number2atol(long(quantity), width)

    def atol2quantity(self, quantity):
        """Преобразование из формата ккм (МДЕ) в количество.

        <1>стр.17"""
        return self.atol2number(quantity) / self._quantityPrecision

    def date2atol(self, date):
        return date

    def atol2date(self, date):
        return date

    def time2atol(self, time):
        return time

    def atol2time(self, time):
        return time

    ### Запросы

    def GetLastSummary(self):
        """Запрос последнего сменного итога.
        <1>стр.28
        """
        try:
            return self.atol2money(
                checkException(
                self._atol_send_data(self._kkmPassword + _atol_GetLastSummary_cmd)
                )[2:]
                )
        except IndexError:
            raise KKMUnknownAnswerErr

    def GetStatus(self):
        ans = self._atol_send_data(self._kkmPassword + _atol_GetStatus_cmd)
        try:
            if (ans[0] != 'D'):
                raise KKMUnknownAnswerErr
            cashier = self.atol2number(ans[1])
            site = self.atol2number(ans[2])
            date = self.atol2date(ans[3:6])
            time = self.atol2time(ans[6:9])
            flags = ord(ans[9])
            mashine = self.atol2number(ans[10:14])
            model = ord(ans[14])
            version = ans[15] + '.' + ans[16]
            mode = ord(ans[17]) & 0x0F
            submode = (ord(ans[17]) & 0xF0) >> 4
            check = self.atol2number(ans[18:20])
            smena = self.atol2number(ans[20:22])
            checkState = ord(ans[22])
            checkSum = self.atol2number(ans[23:28])
            dot = ord(ans[28])
            port = ord(ans[29])
        except IndexError:
            raise KKMUnknownAnswerErr
        return (cashier, site, date, time, flags, \
                mashine, model, version, mode, submode, \
                check, smena, checkState, checkSum, dot, port)

    def getKKMId(self):
        """Запрос уникального идентификатора ККМ.
        """
        return self.GetStatus()[5]

    def GetCheckNum(self):
        """Запрос текущего номера чека.
        """
        return self.GetStatus()[10]

    def GetCheckSum(self):
        """Запрос суммы текущего чека.
        """
        return self.GetStatus()[12]

    def GetCurrentState(self):
        """Запрос кода состояния (режима) ККМ.

        Result: mode, submode, printer, paper
        <1>стр.28
        """
        ans = self._atol_send_data(self._kkmPassword + _atol_GetCurrentState_cmd)
        try:
            mode = ord(ans[1]) & 0x0F
            submode = (ord(ans[1]) & 0xF0) >> 4
            printer = (ord(ans[2]) & 0x02) == 1
            paper = (ord(ans[2]) & 0x01) == 1
        except IndexError:
            raise KKMUnknownAnswerErr
        return (mode, submode, printer, paper)

    def GetCurrentMode(self):
        """Запрос режима ККМ
        """
        return self.GetCurrentState()[0]

    _atol_mode1_offline = '\x8000'
    _atol_mode1_online  = '\x4000'
    _atol_mode1_passive = '\x2000'
    _atol_mode1_fiscreg = '\x1000'
    _atol_mode1_fiscard = '\x0800'

    def GetTypeDevice(self):
        """Получение типа устройства.

        Result: error, protocol, type, model, mode,
        majorver, minorver, codepage, build, name
        <1>стр.28,63
        """

        ans = self._atol_send_data(self._kkmPassword + _atol_GetTypeDevice_cmd)
        try:
            if (ord(ans[0]) != 0):
                raiseException(ord(ans[0]))
            error = ans[0]
            protocol = ans[1]
            type_ = ans[2]
            model = ans[3]
            mode = (ord(ans[4]) << 8) | ord(ans[5])
            majorver = ord(ans[6])
            minorver = ord(ans[7])
            codepage = ord(ans[8])
            build = self.atol2number(ans[9:11])
            name = ans[11:]
        except IndexError:
            raise KKMUnknownAnswerErr
        #print 'XMM 5 GetTypeDev', {'error': error, 'protocol': protocol, 'type': type, 'model': model,
        #        'mode': mode, 'majorver': majorver, 'minorver': minorver,
        #        'codepage': codepage, 'build': build, 'name': name}
        return {'error': error, 'protocol': protocol, 'type': type_, 'model': model,
                'mode': mode, 'majorver': majorver, 'minorver': minorver,
                'codepage': codepage, 'build': build, 'name': name}

    def ResetMode(self):
        """Выход из текущего режима.
        """
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_ResetMode_cmd)
            )

    def SetMode(self, mode, modePassword):
        """Установить режим.

        <1>стр.19
        """
        curMode = self.GetCurrentMode()
        if (mode != curMode):
            if (curMode != _atol_Select_mode):
                self.ResetMode()
            checkException(
                self._atol_send_data(self._kkmPassword + _atol_SetMode_cmd + \
                                     self.number2atol(mode) + self.number2atol(modePassword, 8))
                )

    def isRegistrationMode(self):
        return self.GetCurrentMode() == _atol_Registration_mode

    def isXReportMode(self):
        return self.GetCurrentMode() == _atol_XReport_mode

    def isZReportMode(self):
        return self.GetCurrentMode() == _atol_ZReport_mode

    def isProgrammingMode(self):
        return self.GetCurrentMode() == _atol_Programming_mode

    def isInspectorMode(self):
        return self.GetCurrentMode() == _atol_Inspector_mode

    def isCheckOpen(self):
        return self.GetStatus()[12] != 0

    def setRegistrationMode(self, password):
        self.SetMode(_atol_Registration_mode, password)

    def setXReportMode(self, password):
        self.SetMode(_atol_XReport_mode, password)

    def setZReportMode(self, password):
        self.SetMode(_atol_ZReport_mode, password)

    def setProgrammingMode(self, password):
        self.SetMode(_atol_Programming_mode, password)

    def setInspectorMode(self, password):
        raise KKMNotImplementedErr
        self.SetMode(_atol_Inspector_mode, password)

    def initStringMax(self):
        try:
            self._strMax = _modelTable[self.model][_atol_StringMax_idx]
        except KeyError:
            raise KKMUnknownModelErr

    def initKlisheMax(self):
        try:
            self._klisheMax = _modelTable[self.model][_atol_KlisheMax_idx]
        except KeyError:
            raise KKMUnknownModelErr

    def initKlisheLen(self):
        try:
            self._klisheLen = _modelTable[self.model][_atol_KlisheLen_idx]
        except KeyError:
            raise KKMUnknownModelErr

    ### Общие команды

    def PrintString(self, txt, wrap=False):
        """Печать строки на кассовой ленте"""
        idx = 0
        slen = len(txt)
        smax = self.getStringMax()
        while idx <= slen:
            checkException(
                self._atol_send_data(self._kkmPassword + _atol_PrintString_cmd + \
                                     self.str2atol(txt[idx:idx + smax], smax))
                )
            idx += smax
            if not wrap:
                break

    def PrintToDisplay(self, txt):
        """Вывод сообщения на дисплей покупателя"""
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_PrintToDisplay_cmd + \
                                 self.number2atol(1) + \
                                 self.str2atol(txt, self.getDisplayStringMax()))
            )

    def OpenCashBox(self):
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_OpenCashBox_cmd)
            )

    ### Команды режима регистрации
    # <1>стр.34

    def getRegFlags(self):
        flags = 0
        if (self.isTestOnlyMode()):
            flags |= _atol_TestOnly_flag
        if (self.isCheckCashMode()):
            flags |= _atol_CheckCash_flag
        return flags

    def cashPayType( self ):   return _atol_cash_payment
    def creditPayType( self ): return _atol_type2_payment
    def taraPayType( self ):   return _atol_type3_payment
    def cardPayType( self ):   return _atol_type4_payment

    def CashIncome(self, sum_):
        """Внесение денег."""
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_CashIncom_cmd + \
                            self.number2atol(self.getRegFlags()) + self.money2atol(sum_))
            )

    def CashOutcome(self, sum_):
        """Выплата денег (инкасация)."""
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_CashOutcom_cmd + \
                            self.number2atol(self.getRegFlags()) + self.money2atol(sum_))
            )

    _checkTypeDict = {
        kkm.kkm_Sell_check     : 1,
        kkm.kkm_Return_check   : 2,
        kkm.kkm_Annulate_check : 3
        }

    def OpenCheck(self, checkType=kkm.kkm_Sell_check):
        """Открыть Чек.

        <2>стр.44,<3>стр.37"""
        checkException(
            self._atol_send_data(self._kkmPassword + \
                                 _atol_OpenCheck_cmd + self.number2atol(self.getRegFlags()) + self.number2atol(self._checkTypeDict[checkType]))
            )

    def Sell(self, name, price, quantity, department):
        """Продажа.

        Если режим TestOnly включен - выполнить только проверку возможности исполнения.
        Если режим PreTestMode включен - выполнить с проверкой возможности исполнения.
        <1>стр.35
        """
        logger.info('Sell %s, price: %s, quantity: %s, department: %s' % (
                    name, price, quantity, department))
        if (self.isPreTestMode() or self.isTestOnlyMode()):
            checkException(
                self._atol_send_data(self._kkmPassword + _atol_Sell_cmd + \
                                self.number2atol(self.getRegFlags() | _atol_TestOnly_flag) + \
                                self.money2atol(price) + self.quantity2atol(quantity) + \
                                self.number2atol(department))
                )
        if (self.isTestOnlyMode()):
            return
        self.PrintString(name)
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_Sell_cmd + \
                                 self.number2atol(self.getRegFlags()) + self.money2atol(price) + \
                                 self.quantity2atol(quantity) + self.number2atol(department))
            )

    def BuyReturn(self, name, price, quantity):
        """Возврат.

        Если режим TestOnly включен - выполнить только проверку возможности исполнения.
        Если режим PreTestMode включен - выполнить с проверкой возможности исполнения.
        <1>стр.37
        """
        if (self.isPreTestMode() or self.isTestOnlyMode()):
            checkException(
                self._atol_send_data(self._kkmPassword + _atol_Return_cmd + \
                                self.number2atol(self.getRegFlags() | _atol_TestOnly_flag) + \
                                self.money2atol(price) + self.quantity2atol(quantity))
                )
        if (self.isTestOnlyMode()):
            return
        self.PrintString(name)
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_Return_cmd + \
                                 self.number2atol(self.getRegFlags()) + self.money2atol(price) + \
                                 self.quantity2atol(quantity))
            )

    def Discount(self, count, area=kkm.kkm_Sell_dis, \
                  type_=kkm.kkm_Sum_dis, sign=kkm.kkm_Discount_dis):
        """Начисление скидки/надбавки.

        <1>стр.37
        """
        logger.info('Discount : ' + str(count) + '\t' + self.number2atol(count))
        if (area == kkm.kkm_Sell_dis):
            area = 1
        else:
            area = 0
        if (type_ == kkm.kkm_Procent_dis):
            type_ = 0
            count = self.number2atol(count * 100, 5)  # 100.00%
        else:
            type_ = 1
            count = self.money2atol(count)
        if (sign == kkm.kkm_Discount_dis):
            sign = 0
        else:
            sign = 1
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_Discount_cmd + \
                                 self.number2atol(self.getRegFlags()) + \
                                 self.number2atol(area) + \
                                 self.number2atol(type) + \
                                 self.number2atol(sign) + \
                                 count)
            )

    def Annulate(self):
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_Annulate_cmd)
            )

    def Payment(self, sum_, payType=None):
        """Оплата чека с подсчетом суммы сдачи.

        <1>стр.38
        """
        logger.info('Payment : ' + str(sum_) + '\t' + self.money2atol(sum_))
        if (payType == None):
            payType = self.cashPayType()
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_Payment_cmd + \
                                 self.number2atol(self.getRegFlags()) + \
                                 self.number2atol(payType) + self.money2atol(sum_))
            )

    ### Команды режима отчетов без гашения

    def ReportWOClearing(self, reportType):
        """
        """
        import time
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_XReport_cmd + \
                                 self.number2atol(reportType))
            )
        mode, submode, printer, paper = self.GetCurrentState()
        while (mode == 2 and submode == 2):
            time.sleep(_atol_Report_timeout)
            mode, submode, printer, paper = self.GetCurrentState()
            if (mode == 2 and submode == 0):
                if (printer):
                    raise KKMPrinterConnectionErr
                if (paper):
                    raise KKMOutOfPaperErr
                else:
                    return

    ### Команды режима отчетов c гашением

    def ClearingReport(self):
        """
        """
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_ClearingReport_cmd)
            )
        mode, submode, printer, paper = self.GetCurrentState()
        while (mode == 3 and submode == 2):
            time.sleep(_atol_Report_timeout)
            mode, submode, printer, paper = self.GetCurrentState()
            if (mode == 3 and submode == 0):
                if (printer):
                    raise KKMPrinterConnectionErr
                if (paper):
                    raise KKMOutOfPaperErr
                else:
                    return
            else:
                raise KKMReportErr

    def ZReportHold(self):
        """Включить режим формирования отложенных Z отчётов.

        Result: кол-во свободных полей для записи Z-отчётов
        <4>стр.9
        """
        try:
            return ord(checkException(
                self._atol_send_data(self._kkmPassword + _atol_ZReportToMem_cmd)
                )[2])
        except IndexError:
            raise KKMUnknownAnswerErr

    def ZReportUnHold(self):
        """Распечатать отложенные Z-отчёты и отключить режим отложенных Z отчётов.
        """
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_ZReportFromMem_cmd)
            )

    def ZReport(self):
        """
        """
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_ZReport_cmd)
            )
        mode, submode, printer, paper = self.GetCurrentState()
        print '00', mode, submode, printer, paper
        while (mode == 3 and submode == 2):
            print '32-0'
            time.sleep(_atol_Report_timeout)
            print '32-1'
            mode, submode, printer, paper = self.GetCurrentState()
            print '32-2', mode, submode, printer, paper
        if (mode == 7 and submode == 1):
            print '71-0'
            while (mode == 7 and submode == 1):
                print '71-1'
                time.sleep(_atol_Report_timeout)
                print '71-2'
                mode, submode, printer, paper = self.GetCurrentState()
                print '71-3', mode, submode, printer, paper
            return
        else:
            print '??', mode, submode, printer, paper
            if (mode == 3 and submode == 0):
                #return
                raise KKMFiscalMemoryOverflowErr
            if (printer):
                raise KKMPrinterConnectionErr
            if (paper):
                raise KKMOutOfPaperErr
            else:
                raise KKMReportErr

    def CommonClearing(self):
        """
        """
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_CommonClear_cmd)
            )
        mode, submode, printer, paper = self.GetCurrentState()
        while (mode == 3 and submode == 6):
            time.sleep(_atol_Report_timeout)
            mode, submode, printer, paper = self.GetCurrentState()
            if (mode == 3 and submode == 0):
                if (printer):
                    raise KKMPrinterConnectionErr
                if (paper):
                    raise KKMOutOfPaperErr
                else:
                    return
            else:
                raise KKMReportErr

    _reportTable = {
        kkm.kkm_Clearing_report: (ClearingReport, None),
        kkm.kkm_Z_report: (ZReport, None),
        kkm.kkm_X_report: (ReportWOClearing, 1),
        kkm.kkm_Department_report: (ReportWOClearing, 2),
        kkm.kkm_Cashier_report: (ReportWOClearing, 3),
        kkm.kkm_Goods_report: (ReportWOClearing, 4),
        kkm.kkm_Hour_report: (ReportWOClearing, 5),
        kkm.kkm_Quantity_report: (ReportWOClearing, 7)
        }

    def Report(self, type_):
        """
        """
        try:
            if (self._reportTable[type_][1] != None):
                self._reportTable[type_][0](self, self._reportTable[type_][1])
            else:
                self._reportTable[type_][0](self)
        except KeyError:
            raise KKMReportErr(u'Неизвестный тип отчета')

    ### Команды режима программирования
    # <1>стр.44

    def readTable(self, table, row, field):
        try:
            return checkException(
                self._atol_send_data(self._kkmPassword + _atol_ReadTable_cmd + \
                                     self.number2atol(table) + self.number2atol(row, 4) + \
                                     self.number2atol(field))
                )[2:]
        except IndexError:
            raise KKMUnknownAnswerErr

    def _writeTable(self, table, row, field, value):
        return checkException(
            self._atol_send_data(self._kkmPassword + _atol_Programming_cmd + \
                                 self.number2atol(table) + self.number2atol(row, 4) + \
                                 self.number2atol(field) + value)
            )

    _progTable = {  # (table,row,field,bitmask,type,length,{None|dict|func})
        'kkmNumber':          (2,1,1,None,'int',1,None),
        'multiDepart':        (2,1,2,None,'int',1,{'multi':0,'single':1}),
        'taxType':            (2,1,11,None,'int',1,{'deny':0,'all':1,'sell':2}),
        'departName':         (2,1,15,None,'int',1,{0:0,1:1}),
        'printNotClearedSum': (2,1,18,0b00000011,'bin',1,{False:0,'deny':0,'all':0b00000001,'last':0b00000011,True:0b11}),
        'makeIncasation':     (2,1,18,0b00000100,'bin',1,{False:0,True:0b00000100}),
        'extendedZreport':    (2,1,18,0b00001000,'bin',1,{False:0,True:0b00001000}),
        'pushLength':         (2,1,22,0b00000111,'bin',1,None),  # 0..15
        'onCutCheck':         (2,1,22,0b00110000,'bin',1,{'save':0,'push':0b010000,'drop':0b110000}),
        'prevCheck':          (2,1,22,0b01000000,'bin',1,{'save':0,'drop':0b1000000}),
        'startCheck':         (2,1,22,0b10000000,'bin',1,{'loop':0,'push':0b10000000}),
        'kkmPassword':        (2,1,23,None,'int',2,None),
        'cutDocument':        (2,1,24,None,'int',1,{False:0,True:1}),
        'setPayCreditName':   (12,1,1,None,'string',10,None),
        'setPayTaraName':     (12,2,1,None,'string',10,None),
        'setPayCardName':     (12,3,1,None,'string',10,None)
        }

    def Programming(self, args):
        """Программирование ККМ.

        args в виде {'параметр': значение,}
        """
        try:
            for k in args.keys():
                table, row, field, bitmask, rtype, length, trans = self._progTable[k]
                if (trans == None):
                    value = args[k]
                elif (type(trans) == type({})):  # Dict
                    value = trans[args[k]]
                elif (str(type(trans)) == str(type(lambda x: x))):  # function
                    value = trans(args[k])
                else:
                    raise KKMNotImplementedErr
                if (bitmask != None):
                    oldValue = ord(self.readTable(table, row, field))
                    print 'P0 %s %s' % (oldValue, bin(oldValue))
                    #oldValue = self.atol2number(oldValue)
                    print 'P1 %s | (%s & ~%s), %s' % (bin(value), bin(oldValue), bin(bitmask), bin(oldValue & ~bitmask))
                    value |= (oldValue & ~bitmask)
                    print 'P2', bin(value), chr(value), 'AA'
                    value = chr(value)
                    #value = self.number2atol(value, length * 2)
                elif (rtype == 'string'):
                    value = self.str2atol(value, length)
                elif (rtype == 'int'):
                    value = self.number2atol(value, length * 2)  # по 2 знака на байт!
                else:
                    raise KKMNotImplementedErr
                self._writeTable(table, row, field, value)
        except KeyError:
            raise KKMNotImplementedErr

    def setKKMPassword(self, password):
        self._kkmPassword = self.number2atol(password, 4)
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_Programming_cmd + \
                                 self.number2atol(2) + self.number2atol(1, 4) + \
                                 self.number2atol(23) + self._kkmPassword)
            )

    def setCashierPassword(self, cashier, password):
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_Programming_cmd + \
                                 self.number2atol(3) + self.number2atol(cashier, 4) + \
                                 self.number2atol(1) + self.number2atol(password, 8))
            )

    def setAdminPassword(self, password):
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_Programming_cmd + \
                                 self.number2atol(3) + self.number2atol(29, 4) + \
                                 self.number2atol(1) + self.number2atol(password, 8))
            )

    def setSysAdminPassword(self, password):
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_Programming_cmd + \
                                 self.number2atol(3) + self.number2atol(30, 4) + \
                                 self.number2atol(1) + self.number2atol(password, 8))
            )

    def setKlishe(self, klishe):
        """Установить клише/рекламу в чеке.

        параметр klishe - список строк.
        <1>стр.78
        """
        i = 1
        for s in klishe:
            checkException(
                self._atol_send_data(self._kkmPassword + _atol_Programming_cmd + \
                                     self.number2atol(6) + self.number2atol(i, 4) + \
                                     self.number2atol(1) + self.str2atol(s, self.getKlisheLen()))
            )
            i += 1
        for j in range(i, self.getKlisheMax()):
            checkException(
                self._atol_send_data(self._kkmPassword + _atol_Programming_cmd + \
                                     self.number2atol(6) + self.number2atol(j, 4) + \
                                     self.number2atol(1) + self.str2atol(s, self.getKlisheLen()))
            )

    def setDepartName(self, depart, name):
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_Programming_cmd + \
                                 self.number2atol(7) + self.number2atol(depart, 4) + \
                                 self.number2atol(1) + self.str2atol(name, 20))
            )

    def setTaxRate(self, tax, value):
        checkException(
            self._atol_send_data(self._kkmPassword + _atol_Programming_cmd + \
                                 self.number2atol(8) + self.number2atol(tax, 4) + \
                                 self.number2atol(1) + self.number2atol(value, 4))
            )
