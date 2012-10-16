# -*- coding: UTF-8 -*-
# Copyright (c) 2005,2007
# Marat Khayrullin <xmm.dev@gmail.com>

# ВНИМАНИЕ!
# Этот файл НЕ ЯВЛЯЕТСЯ частью драйвера kkm, поэтому его НЕЛЬЗЯ использовать в проектах!
# Он только демонстрирует принципы работы с драйвером.
#

# Инициализация фискальника
    if mode != 1:
        try:
            self.kkm = kkmDev = kkm.KkmMeta.autoCreate()
            kkmSerialNumber = kkmDev.getKKMId()
        except Exception, msg:
            self.mode = 1
            self.ShowError(msg or 'Не найден кассовый аппарат или не определён серийный номер.')
            raise


# Регистрация пользователя на фискальнике
    if self.mode != 1:
        kkmDev = self.kkm
        try:
            kkmDev.setRegistrationMode(30)
            if kkmDev.isCheckOpen():
                kkmDev.Annulate()
        except kkm.Exception.KKMException, msg:
            self.ShowError(msg)
        try:
            kkmDev.ResetMode()
        except kkm.Exception.KKMException, msg:
            self.ShowError(msg)


# Продажа позиции (регистрация в ккм)

    kkmDev.Sell(name.strip(), float(price.strip()), float(count.strip()), 0)


# Проведение оплаты
    try:
        if mode != 1:
            for item in xrange(itemlist):
               name, count, price, discount, sum = item.getinfo()
               kkmDev.Sell(name.strip(), float(price.strip()), float(count.strip()), 0)
               discount = float(discount.strip())
               if discount:
                   kkmDev.Discount(discount) # Скидка на позицию
            discount = float(str(itemlist.discount).strip())
            if discount:
                kkmDev.Discount(discount, kkm.kkm_Check_dis) # Скидка на весь чек
            if self.mode == 0:
                kkmDev.Payment(payment) # Оплата
            else:
                kkmDev.Annulate()
    except kkm.Exception.KKMException, msg:
        try:
            kkmDev.ResetMode()
        except kkm.Exception.KKMException, msg:
            self.ShowError(msg)

    else:
        try:
            if mode != 1:
                kkmDev.PrintToDisplay('\x0C')
                kkmDev.PrintToDisplay('')
                max = kkmDev.getDisplayStringMax()
                kkmDev.PrintToDisplay('Спасибо'.center(max))
                kkmDev.PrintToDisplay('за покупку!'.center(max))
        except:
            pass
