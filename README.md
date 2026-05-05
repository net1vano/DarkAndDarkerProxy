# [RU] Прокси для Dark and Darker
Прокси для запуска Dark and Darker без всяких костылей ввиде WARP и VPN.  

*UDP. тех, кто сидит через варп и амнезию на прокси - буду вводить geoIP только для России.   
Потому что участились случаи захода через варп и амнезию на мою прокси.  
Проблема не в том, что вам так удобней или проще, а в том, что вы делаете двойную петлю и только усугбляете своё соединение.  
потратьте 10 минут своего времени в правильной настройке*

Ничего скачивать НЕ НУЖНО. Код для тех, кто захочет развернуть самостоятельно или проверить как работает прокси изнутри.  
  
В данный момент сервис проксирует только игровой координатор, который отвечает за главное меню. Если в главное меню зашло - значит прокси отработала. 


## Самостоятельная настройка запрета.
 
Чтобы зашло в матч нужно настроить запрет.   
в `service.bat` нужно обновить IPset, затем включить `Gamefilter` в режим `TCP+UDP`.   
`IPset filter` - `loaded`.  
И после этого - подбирать батник, пока не пустит в игру. Обычно это ваш основной батник. (для тестов лучше заходить в ПВЕ без вещей) 


## Готовый запрет.
Скачать из [релиза](https://github.com/net1vano/DarkAndDarkerProxy/releases) архив: `https://github.com/net1vano/DarkAndDarkerProxy/releases`  
подобрать рабочую стратегию для своего интернета.  
[Hyperion](https://hyperion-cs.github.io/dpi-checkers/ru/tcp-16-20/)   
здесь можете проверить насколько хорошо всё работает. чем больше OK тем лучше.  
После запуска нового батника - обновлять страницу для чистоты эксперимента.


  

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

## Известные проблемы
1) Новые версии запрета =>1.9.8 не позволяют догружаться в матч. Чинится либо возвращением стратегии из старого запрета, либо адаптацией из новой версии. Чинить все батники у меня сил не хватит, поэтому адаптировал ДС под старую версию.
2) Всё сделал, не пускает в главное меню. Либо идет переадресация (варп, амнезия, пнв), либо в запрет не добавлен IP прокси.
3) Всё сделал, не пускает в игру. Здесь нужно проверить все настройки запрета.
    Если скачали архив, то одна из стратегий должна помочь, если нет - пишите в личку.
   Если сами делали, то перепроверить все флаги и параметры запуска.
4) Всё выключено, не пускает в меню. Скорее всего не добавили IP в файл хостс. Или не запустили от администратора блокнот.


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
