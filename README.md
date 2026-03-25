# [RU] Прокси для Dark and Darker
Прокси для запуска Dark and Darker без всяких костылей ввиде WARP и VPN. 

## Как использовать
добавьте данную строку в файл hosts  

144.31.182.245 live-gateway.lunatichigh.net  

затем сохраните файл (возможно потребуются права администратора). 
Если потребовались права, то сохраните в другое место с таким же названием и без .txt в конце. Затем копируйте файл в  
[буква диска на которой расположена ОС]:\Windows\System32\drivers\etc\  

в конце последовательно выполните WIN+R  
cmd  
ipconfig /flushdns  



# Правила использования  

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
