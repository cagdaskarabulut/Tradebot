from django.conf.urls import url, include
from django.conf.urls.static import static
from django.conf import settings
from .views import *

urlpatterns = [
    url(r'^$', mainPage, name='mainPage'),
    url(r'^mainPage/$', view=mainPage, name='mainPage'),
    url(r'^activeTrades/$', activeTrades, name='activeTrades'),
    url(r'^chart/$', chart, name='chart'),
    url(r'^actions/$', actions, name='actions'),
    url(r'^changePanicModeAction/$', view=changePanicModeAction, name='changePanicModeAction'),
    url(r'^buyWithFullAutomaticallyAction/$', view=buyWithFullAutomaticallyAction, name='buyWithFullAutomaticallyAction'),
    url(r'^buyWithDolarValueAction/$', view=buyWithDolarValueAction, name='buyWithDolarValueAction'),
    url(r'^sellAllByCoinAction/$', view=sellAllByCoinAction, name='sellAllByCoinAction'),
    url(r'^sellAllByTradeAction/$', view=sellAllByTradeAction, name='sellAllByTradeAction'),
    url(r'^addOrRemoveBudgetFromRobotAction/$', view=addOrRemoveBudgetFromRobotAction, name='addOrRemoveBudgetFromRobotAction'),
    url(r'^resetDraftUsdtDiffAction/$', view=resetDraftUsdtDiffAction, name='resetDraftUsdtDiffAction'),
    url(r'^export/xls/$', view=export_tradesHistory_xls, name='export_tradesHistory_xls'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
