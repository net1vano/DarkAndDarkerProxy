# [RU] Прокси для Dark and Darker
Прокси для запуска Dark and Darker без всяких костылей ввиде WARP и VPN. 

Ничего скачивать НЕ НУЖНО. Код для тех, кто захочет развернуть самостоятельно или проверить как работает прокси изнутри.  
  
В данный момент сервис проксирует только игровой координатор, который отвечает за главное меню. Если в главное меню зашло - значит прокси отработала.  
Чтобы зашло в игру нужно настроить запрет. в `service.bat` нужно обновить IPset, затем включить `Gamefilter` в режим `TCP+UDP`. `IPset filter` - `loaded`.  
И после этого - подбирать батник, пока не пустит в игру (для тестов лучше ПВЕ без вещей)  

  

## Как использовать
добавьте `144.31.182.245` в `zapret/lists/ipset-exclude.txt`  

<kbd>WIN</kbd> + <kbd>R</kbd>  
`notepad %windir%/system32/drivers/etc/hosts`  
<kbd>CTRL</kbd>+<kbd>SHIFT</kbd>+<kbd>ENTER</kbd> - чтобы запустить блокнот от имени администратора


добавьте данную строку в файл hosts  
`144.31.182.245 live-gateway.lunatichigh.net`

Затем сбросить кеш DNS реестра для сброса старых маршрутов  
<kbd>WIN</kbd> + <kbd>R</kbd>   
`ipconfig /flushdns`  


Чтобы перестать пользоваться выполните те же шаги, только удалите строчку из файла


# Правила использования  

Я никак не монетизирую своё решение, сделано оно в первую очередь для сбора статистики и выбора тактики решения проблемы. Обезличенная статистика (количество подключений, средний онлайн через мою прокси) будет отправлена разработчикам в случае диалога с тех.разработчиками игры для помощи в разработке их решения, встроенного в архитектуру игры.

В данный момент использование прокси не нарушает ToS игры, тех. поддержка Ironmace ответила по поводу создания своего прокси для РУ сегмента:  

We are continuously reviewing ways to improve access for users across various regions,  
but we are unable to share specific timelines or details at this time.   
We appreciate your patience and understanding.  


Regarding network connection methods, we are not in a position to recommend or guide users toward specific approaches.  
Additionally, internal technical information such as protocol structures cannot be disclosed for security reasons.  
We hope you understand.


# Dark And Darker Proxy
Transparent proxy for resolve connectivity problems with Dark and Darker servers

## How to use
add  
144.31.182.245 live-gateway.lunatichigh.net  
to hosts file and perform ipconfig /flushdns  

## How it works
Proxy catch json answer from DaD coordinator and replace Game Server ip to its own.
