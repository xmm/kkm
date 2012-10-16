# -*- coding: UTF-8 -*-
# Copyright (c) 2005, 2012
# Marat Khayrullin <xmm.dev@gmail.com>

# Возможные значения переменной checkType в методе OpenCheck
kkm_Sell_check          = 0
kkm_StornoSell_check    = 1
kkm_Return_check        = 2
kkm_StornoReturn_check  = 3
kkm_Buy_check           = 4
kkm_StornoBuy_check     = 5
kkm_Annulate_check      = 6

# Discount options
kkm_Check_dis    = 0 # Скидка на чек
kkm_Sell_dis     = 1 # Скидка на позицию
kkm_Procent_dis  = 0 # Процентная скидка
kkm_Sum_dis      = 1 # Скидка суммой
kkm_Discount_dis = 0 # Скидка
kkm_Increase_dis = 1 # Надбавка

# Report Types
kkm_Clearing_report   = 1
kkm_Z_report          = 2
kkm_X_report          = 3
kkm_Department_report = 4
kkm_Cashier_report    = 5
kkm_Goods_report      = 6
kkm_Hour_report       = 7
kkm_Quantity_report   = 8

import logging
logger = logging.getLogger('kkm')


class KkmMeta(type):
    __registry = {}

    def __init__(cls, name, base, dict):
        if name != 'KKM':
            print 'KkmMeta.__init__', name, cls
            cls.__registry[name] = cls

    def autoCreate(cls, portParams=None, password=0):
        import os, Exception
        if not portParams:
            if os.name == 'posix':
                portParams = {'port': '/dev/kkm', 'baudrate': 9600}
            elif os.name == 'nt':
                portParams = {'port': 2, 'baudrate': 9600}
            else:
                logger.critical(u'Не поддерживаемая платформа')
                raise Exception.KKMCommonErr(u'Не поддерживаемая платформа')
        for kkm in cls.__registry.values():
            try:
                print 'KkmMeta.autoCreate', kkm, portParams, password
                return kkm(portParams, password)
            except Exception.KKMException:
                pass
        logger.critical(u'Нет связи с ККМ или неизвестная модель ККМ')
        raise Exception.KKMCommonErr(u'Нет связи с ККМ или неизвестная модель ККМ')
    autoCreate = classmethod(autoCreate)


class KKM:
    "Абстактный базовый класс поддержки Контрольно-Кассовых Машин."

    __metaclass__ = KkmMeta

    _kkm               = None       # Файловый дескриптор драйвера
    _kkmPassword       = None       # Пароль доступа к ККМ
    _device            = {}
    _speed             = 0

    # Значения специфичные для конкретных моделей ККМ
    _passwordLen       = 4          # Длина пароля
    _moneyWidth        = 10         # Кол-во разрядов
    _quantityWidth     = 10         # Кол-во разрядов
    _stringMax         = 20         # Максимальное значение
    _displayMax        = 20         # Максимальная длина строки для вывода на дисплей пользователя
    _moneyMax          = 9999999999 # Максимальное значение (учитывая _moneyPrecision)
    _quantityMax       = 9999999999 # Максимальное значение (учитывая _quantityPrecision)
    _moneyPrecision    = 100  # Точность денежной единицы после десят. точки (в виде множителя)
    _quantityPrecision = 1000 # Точность единицы измерения веса после десят. точки (в виде множителя)

    _testOnly  = 0
    _checkCash = 1
    _preTest   = 1 # Флаг выполнения команд в режиме регистрации
                   #   с предварительной проверкой исполнимости

    def __init__(self, device, password):
        self._kkmPassword = password
        self.InitDevice(device)
        #print 'XMM __init__kkm 0: ', self._kkm

    def InitDevice(self, device):
        self._device = device
        self.OpenDevice()
        import atexit
        atexit.register(self.CloseDevice)

    def OpenDevice(self): pass
    def CloseDevice(self):
        import Exception
        try:
            self._kkm.close()
        except:
            logger.critical('Can\'t close KKM device.')
            raise Exception.KKMCommonErr('Can\'t close KKM device.')

    def isRegistrationMode( self ): pass
    def isXReportMode( self ): pass
    def isZReportMode( self ): pass
    def isProgrammingMode( self ): pass
    def isInspectorMode( self ): pass
    def isCheckOpen( self ): pass

    def setRegistrationMode( self, password ): pass
    def setXReportMode( self, password ): pass
    def setZReportMode( self, password ): pass
    def setProgrammingMode( self, password ): pass
    def setInspectorMode( self, password ): pass

    def isTestOnlyMode( self ):  return self._testOnly
    def isPreTestMode( self ):   return self._preTest
    def isCheckCashMode( self ): return self._checkCash

    def setTestOnlyMode( self, bool ):  self._testOnly  = bool
    def setPreTestMode( self, bool ):   self._preTest   = bool
    def setCheckCashMode( self, bool ): self._checkCash = bool

    #gettypekkm
    #state

    def getKKMId( self ):            pass
    def getKKMPassword( self ):      return self._kkmPassword
    def getPasswordLen( self ):      return self._passwordLen
    def getMoneyWidth( self ):       return self._moneyWidth
    def getQuantityWidth( self ):    return self._quantityWidth
    def getStringMax( self ):        return self._strMax
    def getDisplayStringMax( self ): return self._displayMax
    def getKlisheLen( self ):        return self._klisheLen
    def getKlisheMax( self ):        return self._klisheMax

    def OpenCheck( self, checkType ): pass
    def Sell( self, name, price, quantity, department ): pass
    def BuyReturn( self, name, price, quantity ): pass
    def Annulate( self ): pass
    def Storno( self ): pass
    def Payment( self, sum, payType = None ): pass # default: cash
    def Discount( self, count, area = kkm_Sell_dis, \
                  type = kkm_Sum_dis, sign = kkm_Discount_dis): pass
    def CloseCheck( self ): pass
    def CashIncome( self, sum ):  pass
    def CashOutcome( self, sum ): pass
    
    def Report( self, type ):   pass
    def GetLastSummary( self ): pass
    def GetCheckNum( self ):    pass
    def GetCheckSum( self ):    pass

    def PrintString( self, msg ): pass
    def PrintToDisplay( self, msg ): pass
    def OpenCashBox( self ): pass
    def SetCheckHeader( self ): pass
    def SetCheckTail( self ): pass

    def cashPayType( self ): pass
    def creditPayType( self ): pass
    def taraPayType( self ): pass
    def cardPayType( self ): pass

    # Args <1>стр.74:
    #  kkmNumber [1-99] - Номер ККМ в магазине
    #  multiDepart ['multi','single'] - Одна или несколько секций
    ##  payTypes (credit,tara,card)
    ##  useArea ['trade'|'service'|'restrant'|'oil']
    ##  checkFont [0/1] normal/condenced
    ##  ctrltapeFont [0/1] normal/condenced
    #  taxType ['deny'|'all'|'sell'] запрещено, на весь чек, на каждую продажу
    #  departName [0|1] deny/allow print
    #  printNotClearedSum [0|1|2] deny/allow/с момента регистрации
    #  makeIncasation [0|1]
    ##  printBrightness [0..3] min/средняя/норма/высокая
    # Args <1>стр.78:
    #  
    def Programming( self, **args ): pass
    def setKKMPassword( self, password ): pass
    def setCashierPassword( self, cashier, password ): pass
    def setAdminPassword( self, password ): pass
    def setSysAdminPassword( self, password ): pass
    def setKlishe( self, klishe ): pass
    def setDepartName( self, depart, name ): pass
    def setTaxRate( self, tax, value ): pass

