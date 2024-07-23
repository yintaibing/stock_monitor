@echo off
if "%1" == "h" goto begin
mshta Vbscript:createobject("wscript.shell").run("%~nx0 h",0)(window.close)&&exit
:begin
::下面是你自己的代码。
python ./__main__.py