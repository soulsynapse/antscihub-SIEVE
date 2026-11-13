# The ledger costs a cold window walk one and a half to four percent of its fast walks, inside a spread twenty times that

2026-11-12, on v5-monitor at 989dce68, by `docs/findings/experiments/2026-11-12-what-the-trace-costs.py`. The
walk is the Worker's window walk of `video-tests/purb-settings.json`, 600 rows from row 0, its bake live, cold
on a fresh Graph and Decoder each time, the GUI thread turning its loop as the player's does. Kendrick's
player was closed for both sets; a set begun with it open is not in the tables.

Five consumers of the stream. `bare` is `on_event` unset, where a walk pays the demand's context manager at
each entry and nothing else. `drop` is a consumer that does nothing, so every event is built, the hits are
counted and the progress payloads made, and none is kept: the stream's facts emitted to no one. `ledger` is a
Ledger no reader takes a view of, so the worker folds its own queue at each 4096 events. `read` is a Ledger
whose view the GUI thread takes every 250 ms and hands to a catalogue `Log`, which is a window's work less
its painting. `dump` is a `trace.Dump`.

## What was measured

Every walk, ms, in the order run. First set: one consumer a process, six walks each, four rounds.

| consumer | round 1 | round 2 | round 3 | round 4 |
|---|---|---|---|---|
| bare | 1283 1307 1598 1496 1484 1522 | 1328 1362 1445 1335 1333 1320 | 1565 1956 1756 1826 1907 1841 | 1377 1330 1392 1333 1284 1322 |
| drop | 1450 1366 1435 1330 1339 1424 | 1430 1368 1597 1764 2037 1814 | 1495 1751 2056 1909 1983 1835 | 1402 1297 1285 1414 1342 1381 |
| ledger | 1379 1388 1443 1381 1406 1651 | 1476 1399 1384 1378 1451 1694 | 1467 1464 1841 1297 1298 1570 | 1498 1345 1359 1361 1420 1551 |
| read | 1392 1383 1398 1447 1675 1765 | 1464 1414 1559 1477 1413 1427 | 1407 1597 1961 1799 1567 1692 | 1369 1388 1377 1383 1421 1420 |
| dump | 1392 1476 1657 1964 1910 1705 | 1396 1376 1487 1387 1553 1970 | 1344 1381 1695 1370 1423 1432 | 1403 1430 1356 1410 1296 1383 |

Second set: the five walked in turn, walk by walk, in one process, ten times round, three processes; each
column of a round is five walks run one after another.

| consumer | round 1 | round 2 | round 3 |
|---|---|---|---|
| bare | 1270 1778 1303 1699 1304 1327 1558 1481 1760 1865 | 1464 1293 1400 1809 1333 1552 1510 1341 1749 1286 | 1604 1606 1765 1372 1365 1408 1528 1802 2354 1875 |
| drop | 1402 1821 1348 1380 1396 1581 1607 1601 1294 1974 | 1413 1664 1304 1414 1475 1624 1593 1386 1373 1386 | 1709 1910 1921 1302 1377 1875 2385 1870 1365 1947 |
| ledger | 1951 1718 1321 1452 1359 1748 2052 1609 1347 1936 | 1341 1506 1335 1442 1401 1570 1857 1373 1357 1432 | 1926 1673 1480 1306 1330 1888 1952 1974 1653 1943 |
| read | 1879 1549 1396 1365 1709 1718 1679 1573 1437 2523 | 1426 1402 1329 1413 2058 1563 1348 1400 1386 1960 | 1731 1622 1460 1365 1841 1645 1911 1947 1930 2482 |
| dump | 1948 1566 1486 1425 1465 1593 1597 1656 1435 1995 | 1405 1402 1427 1370 1943 1618 1329 1367 1365 1661 | 2068 1702 1800 1433 1424 1721 2025 1466 1926 1922 |

Each set's walks in order of size:

| consumer | set | least | lower quartile | median | upper quartile | most |
|---|---|---|---|---|---|---|
| bare | one a process | 1283 | 1328 | 1384 | 1590 | 1956 |
| drop | one a process | 1285 | 1366 | 1432 | 1802 | 2056 |
| ledger | one a process | 1297 | 1378 | 1413 | 1492 | 1841 |
| read | one a process | 1369 | 1394 | 1424 | 1590 | 1961 |
| dump | one a process | 1296 | 1382 | 1416 | 1631 | 1970 |
| bare | in turn | 1270 | 1339 | 1519 | 1761 | 2354 |
| drop | in turn | 1294 | 1379 | 1528 | 1833 | 2385 |
| ledger | in turn | 1306 | 1358 | 1538 | 1898 | 2052 |
| read | in turn | 1329 | 1402 | 1598 | 1887 | 2523 |
| dump | in turn | 1329 | 1425 | 1580 | 1830 | 2068 |

At the clip's rate the walks run from 4.0 to 7.9 times realtime under every consumer, bare among them.

## What it says

A walk with nothing attached takes anywhere from 1270 to 2354 ms, and about half the walks, under every
consumer and under none, take 200 ms to a second more than the fast ones. Against that no consumer is told
from bare by its median or its upper half: the orderings there change between the two sets.

The fast walks are steadier and do order. By the lower quartile the ledger is 20 to 50 ms above bare, the
ledger read at 250 ms 63 to 66 ms above, the dump 54 to 86 ms, and the dropped events 38 to 40 ms, against a walk of
about 1330: one and a half to four percent for the ledger, four to five read. The fourth round of the first
set, the one stretch in which no walk was slow, says the same: bare 1284 to 1392, the ledger 1345 to 1551,
read 1369 to 1421. The read ledger's fastest walk is above bare's fastest in both sets, by 86 and 59 ms. None
of these was tested for more than its order across two sets, and the dropped events sitting as high as the
ledger says most of what is seen is building the events and not keeping them.

For the fork in `docs/spec/monitor.md`: the walk's rate with the ledger attached is inside the run-to-run
spread of the rate with nothing attached, at every point of it. The spread is seven hundred to eleven hundred
milliseconds wide and the ledger's cost is a few hundredths of that, so the spread admits it easily; the criterion would have
admitted a cost several times this one.

## What is not known

What the slow walks are. They are the walk's and not a consumer's, since bare has them; the probe-cost
finding of the same day met one fill in four slow on `bench.py`'s graph and pointed at the memo's allocation
without taking it apart. They are the larger effect here by an order of magnitude.

A walk long enough for the memo to pass its limit, where every row emits a discard and the ledger keeps each
against a later recomputation, or for the buckets to reach their history; the clip walk was left out on
Kendrick's word. The ledger's cost a row there may differ from a window's.

The window, which did not exist: its painting, at any size. `read` is its polling and detecting alone.

Any document but purb-settings, and a bake served.

## Second half: the window open, at each of its sizes

2026-11-12, on v5-monitor over 5ceb287a with the window's deliverable uncommitted in the tree, by the same
experiment, which now takes `window`, `full` and `small`: the monitor's window open on the walk's ledger,
polled at 250 ms, at the size it opens at, full screen, and at its smallest, on the screen and not offscreen.
The ledger there is attached as the player attaches it, its folding on the worker timed into the stream. Six
consumers walked in turn, ten times round, in two processes. A third was stopped: the experiment opens a
window a walk, and Kendrick, at the machine, asked what was opening. So the desktop was in use for both, and
the player's state was not controlled as it was for the first half.

Every walk, ms, in the order run; each column of a process is six walks run one after another.

| consumer | process 1 | process 2 |
|---|---|---|
| bare | 894 1183 1142 989 984 1037 1037 1277 1076 1146 | 767 1162 775 915 873 965 762 814 766 815 |
| ledger | 912 1271 1170 1112 1214 1235 1076 1021 1054 1293 | 775 1361 811 1132 754 1068 847 770 772 806 |
| read | 1139 1105 935 1015 1072 1032 1215 1080 1350 1119 | 802 1142 1014 1167 776 904 832 811 778 793 |
| window | 1222 1029 882 1205 1118 1023 1154 847 919 838 | 1143 1155 1103 839 942 830 829 1073 1302 1174 |
| full | 1219 1060 866 1264 988 963 1064 1250 851 902 | 1158 1022 1332 1289 973 842 941 1200 1302 1101 |
| small | 1324 1014 1159 1088 1283 1012 1104 1221 828 938 | 1047 1088 806 1008 993 970 816 1060 1122 1251 |

| consumer | process | least | lower quartile | median | upper quartile | most |
|---|---|---|---|---|---|---|
| bare | 1 | 894 | 988 | 1056 | 1155 | 1277 |
| ledger | 1 | 912 | 1046 | 1141 | 1244 | 1293 |
| read | 1 | 935 | 1028 | 1092 | 1158 | 1350 |
| window | 1 | 838 | 873 | 1026 | 1167 | 1222 |
| full | 1 | 851 | 893 | 1024 | 1227 | 1264 |
| small | 1 | 828 | 994 | 1096 | 1236 | 1324 |
| bare | 2 | 762 | 767 | 814 | 928 | 1162 |
| ledger | 2 | 754 | 772 | 808 | 1084 | 1361 |
| read | 2 | 776 | 789 | 822 | 1046 | 1167 |
| window | 2 | 829 | 837 | 1088 | 1160 | 1302 |
| full | 2 | 842 | 965 | 1130 | 1292 | 1332 |
| small | 2 | 806 | 932 | 1028 | 1096 | 1251 |

The walks run from 7.4 to 13.3 times realtime, where the first half's ran 4.0 to 7.9 on the same document and
rows; bare is among them, so it is the machine or the tree since 989dce68 and no consumer, and it was not
taken apart.

The two processes do not agree. In the second, where bare's fast walks sit within a few ms of one another,
the window open is above bare at every point: its fastest walk by 44 to 80 ms, six to ten percent, and its
median by 214 to 316 ms, a quarter to two fifths, with the window at the size it opens at slower than the
bare walk of its own round in seven rounds of ten. In the first, where bare itself spreads from 894 to 1277,
that window and the full screen one are below bare at the least, the lower quartile and the median, the
smallest within 40 ms of it at each, and the window is slower than its round's bare walk in four of ten. The
sizes do not order in either: full screen is the highest by the median in the second process and the lowest
in the first.

So the window's cost to the walk is not settled by this. The most that the second process shows is a
quarter to two fifths at the median, which is far past the ledger's alone; the least that the first shows
is nothing. What would settle it is the same in more processes on a desktop left alone, and with the window
left open across the walks: a window opened a walk pays its first layout and paints inside that walk, which
a window already open in the player does not, so these figures are an upper reading of the window as it is
used.
