print('''
Python3-скрипт, который выводит строки той или иной таблицы, содержащей искомые refSNPID.
Подходит для аннотирования наборов SNP.
Версия: V5.
Автор: Платон Быкадоров, 2017-2018.
Лицензия: GNU General Public License version 3.
Поддержать проект: https://money.yandex.ru/to/41001832285976

Сокращения, используемые в документации:
Таблицы с искомыми SNP далее будут называться "пользовательскими".
Таблица, в которой ищем SNP, далее будет называться "базой".

Один из столбцов "пользовательских" таблиц должен содержать идентификаторы однонуклеотидных полиморфизмов (refSNPID вида rs1234567890).
Скрипт самостоятельно обнаружит столбец с refSNPID в любой таблице (даже если в разных таблицах разный номер rs-столбца).
Также скрипт не растеряется, если в rs-столбце присутствуют иные данные, точки, прочерки и т.д..
rs-столбец может быть единственным столбцом "пользовательской" таблицы.
"Пользовательские" таблицы могут содержать заголовок, начинающийся с "#" или "track name".

Скрипт может сократить "базу" по верхнему порогу p-value или иной величины (допустим, q-value).

Примеры "баз" - GTEx-таблицы. Их можно найти по ссылке https://www.gtexportal.org/home/datasets (требуется регистрация).
Скрипт протестирован на нескольких GTEx-таблицах, в частности, Whole_Blood.egenes.annotated.txt архива GTEx_Analysis_v7_eQTL.tar.gz.

В исходной папке не желательно держать файлы, отличные от "пользовательских" таблиц.
Папку для результатов перед выполнением работы лучше оставлять пустой.

Для поиска: Genotype-Tissue Expression (GTEx) project, eQTL, SNP, биоинформатика, программирование, python 3.
''')

def get_ram_size(source_dir):
        '''
        ОС-специфичное получение значения полного объёма оперативной памяти.
        '''
        os_name = os.name
        system_info_temp = os.path.join(source_dir, 'info_temp.txt')

        ##Создание файла, в который будет выводиться подробная информация о компьютере.
        ##Оттуда не без грязных хаков будет извлекаться значение объёма оперативной памяти.
        ##В зависимости от ОС, способы получения и считывания данных о железе будут разными.

        #Windows.
        if os_name == 'nt':
                print('Из-за нерешённой проблемы с кодировками, Windows пока не поддерживается')

                #В Windows вывести информацию о железе позволяет утилита systeminfo.
                #Эти характеристики будут выведены во временный файл,
                #а уже оттуда можно извлечь объём RAM.
                #Если знаете способ попроще - пишите в Issues.
                os.system("systeminfo > {}".format(system_info_temp))
                with open(system_info_temp) as system_info_temp_op:

                        #Извлечение строки, содержащей значение размера оперативной памяти в мегабайтах.
                        ram_size_line = [line for line in system_info_temp_op if line.find('Полный объем физической памяти') != -1][0]

                        #Файл с характеристиками компьютера больше не нужен, поэтому будет удалён.
                        os.remove(system_info_temp)

                        #Получение размера оперативной памяти в байтах.
                        #Исходное значение из systeminfo-файла представлено числом, разделённым пробелами,
                        #поэтому приходится его дополнительно склеивать регулярным выражением.
                        if re.search(r'МБ', ram_size_line) != None:
                                ram_size = int(''.join(re.findall(r'\d+', ram_size_line))) * 1000000
                                return ram_size
                        else:
                                print('Ошибка. systeminfo вывел объём RAM не в МБ')
                                
        #Linux и, возможно, FreeBSD.
        elif os_name == 'posix':

                #Вывод в файл сведений об оперативной памяти с помощью программы free.
                #Флаг -b позволяет выводить значения сразу в байтах.
                os.system("free -b > {}".format(system_info_temp))
                with open(system_info_temp) as system_info_temp_op:

                        #Поиск значения объёма RAM в таблице, сгенерированной программой free.
                        total_col_index = re.split(r'\s+', system_info_temp_op.readline()).index('total')
                        ram_size = int(re.split(r'\s+', system_info_temp_op.readline())[total_col_index])

                        #Файл с информацией об оперативной памяти больше не нужен, поэтому будет удалён.
                        os.remove(system_info_temp)
                        
                        return ram_size
        else:
                print('Скрипт не поддерживает ОС типа ', os_name)

def rs_col_index_search(source_file_op):
        '''
        Поиск индекса "столбца" любой содержащей refSNPID таблицы.
        Таблица подаётся в функцию в виде открытого средствами Питона файла.
        Столбец с refSNPID может быть единственным столбцом таблицы.
        Если во второй строке refSNPID отсутствует (например, в GTEx-базах вместо refSNPID может быть точка),
        то ищем в третьей, если нет и в третьей, движемся дальше по строкам, пока не найдём.
        После нахождения индекса refSNPID-столбца, курсор сбрасывается к началу файла.
        Функция может применяться и для таблиц с хэдерами.
        '''
        for line in source_file_op:
                row = line.split('\t')
                for cell in row:
                        if re.match(r'rs\d+$', cell):
                                rs_col_index = row.index(cell)
                                source_file_op.seek(0)
                                return rs_col_index

def header_save(source_file_op, num_of_headers):
        '''
        Сохранение хэдеров, количество которых должен был указать пользователь, в одномерный массив.
        Если пользователь ввёл значение количества хэдеров, равное 0, создастся пустой список.
        При сохранении хэдеров запомнится позиция курсора считываемого файла.
        Поэтому хэдеры не будут мешать дальнейшей работе с таблицей.
        '''
        headers = [source_file_op.readline() for number in range(num_of_headers)]
        return headers

def table_split(source_file_op, rs_col_index, pval_column, pval_threshold, ram_size, stop_reading):
        '''
        Дробление таблицы на фрагменты, приблизительно
        равные 1/8 объёма оперативной памяти компьютера.
        Фрагменты сортируются по refSNPID-столбцу.
        Один из аргументов функции - уже открытый средствами Питона файл.
        Если этот файл ранее открывался и считывался,
        то в функцию автоматически передастся последняя позиция курсора.
        Т.о., файл начинает считываться со строки, идущей после последней считанной.
        '''

        #При каждом вызове данной функции создаётся пустой список,
        #в который будет накапливаться фрагмент.
        #Также запоминается количество прочитанных к моменту вызова функции байт файла.
        partial_two_dim, init_mem_usage = [], source_file_op.tell()

        #Новый участок файла будет считываться до тех пор,
        #пока разница текущего прочитанного количества байт
        #и зафиксированного в начале вызова функции
        #не достигнет примерно 1/8 объёма оперативной памяти.
        while source_file_op.tell() - init_mem_usage < ram_size // 8:
                
                #Каждая считываемая строка сразу дробится по табуляциям,
                #преобразуясь в список.
                row = source_file_op.readline().split('\t')

                #Считывание файла закончилось, а определённый исходя
                #из объёма RAM предел размера фрагмента не был достигнут.
                #Если на этом месте не остановить цикл while,
                #то к фрагменту начнут присоединяться списки пустых строк.
                #Поэтому, как только встречается первый же список с пустой строкой,
                #накопленный к этому моменту фрагмент сортируется и возвращается функцией.
                #При обнаружения пустого списка функция также
                #возвращает сигнал окончания дробления файла.
                #Этот сигнал реализован в виде изменения значения соответствующей
                #переменной, приводящего к выходу из того цикла while, в котором
                #однократно или многократно вызывается функция дробления.
                if row == ['']:
                        partial_two_dim.sort(key = lambda row: row[rs_col_index])
                        stop_reading = 'yes'
                        return partial_two_dim, stop_reading

                #Если пользователь указал столбец с p-value и порог p-value, то строки,
                #в которых p-value превышает заданный порог, добавляться во фрагмент не будут.
                if pval_column != None and pval_threshold != None:
                        if float(row[pval_column - 1]) > pval_threshold:
                                continue
                
                #Проверка, содержит ли текущая строка refSNPID.
                #В конечный вариант фрагмента не должны попасть строки,
                #содержащие точку или какую-нибудь другую информацию вместо refSNPID.
                if re.search(r'rs\d+$', row[rs_col_index]) != None:

                        #Строка, содержащая SNP-идентификатор, добавляется в список-фрагмент.
                        partial_two_dim.append(row)

        #Считываемый участок файла оказался крупнее 1/8 RAM.
        #Тогда после "естественного" выхода из while
        #функция возвратит накопленный в этом цикле фрагмент
        #файла вместе с сигналом продолжения выполнения
        #цикла, в котором вызывается функция-дробитель.
        partial_two_dim.sort(key = lambda row: row[rs_col_index])
        return partial_two_dim, stop_reading

def table_to_dict(two_dim, rs_col_index):
        '''
        Создание словаря, в котором ключи - refSNPID, а значения - соответствующие refSNPID-содержащие строки таблицы.
        На вход подаётся отсортированная по refSNPID таблица с очищенным столбцом refSNPID,
        без хэдера и, в случае соответствующего пользовательского выбора, с отсечением по p-value.
        Если refSNPID уникален, то соответствующая ему строка таблицы пойдёт в двумерный массив,
        служащий значением этому refSNPID-ключу, и будет представлять собой единственный вложенный список.
        Если же встречается несколько строк подряд с одним и тем же refSNPID,
        добавляем их в качестве элементов двумерного массива, являющегося значением "общему" refSNPID-ключу.
        Чтобы алгоритм выявления одинаковых refSNPID работал и в самом начале формирования словаря,
        первая пара ключ-значение создаётся отдельно.
        '''
        rs_and_ann_dict = {two_dim[0][rs_col_index]: [two_dim[0]]}
        for row_num in range(1, len(two_dim)):
                if two_dim[row_num][rs_col_index] != two_dim[row_num - 1][rs_col_index]:
                        rs_and_ann_dict[two_dim[row_num][rs_col_index]] = [two_dim[row_num]]
                else:
                        rs_and_ann_dict[two_dim[row_num - 1][rs_col_index]] += [two_dim[row_num]]
        return rs_and_ann_dict

def rs_search(two_dim, two_dim_rs_col_index, rs_and_ann_dict, rs_alr_found):
        '''
        Поиск строк базы, содержащих нужные пользователю refSNPID.
        На вход подаётся пользовательский набор refSNPID и соответствующий индекс refSNPID-столбца,
        преобразованная в словарь база, а также множество найденных в предыдущих фрагментах базы refSNPID.
        Это множество пополняется идентификатором сразу же, как только он обнаруживается в базе.
        Если идентификатор уже присутствует во множестве,
        то он не будет искаться в текущем и следующих фрагментах.
        Основной результат - двумерный массив, состоящий из значений,
        соответствующих ключам, совпадающим с пользовательскими refSNPID.
        '''
        out_two_dim = []
        for row in two_dim:
                try:
                        rs_id = row[two_dim_rs_col_index]
                except IndexError:
                        continue
                if rs_id not in rs_alr_found:
                        if rs_id in rs_and_ann_dict:
                                out_two_dim += rs_and_ann_dict[rs_id]
                                rs_alr_found.add(rs_id)
        return out_two_dim, rs_alr_found

####################################################################################################

import os
import csv
import re

us_dir = input('Путь к папке с "пользовательскими" таблицами: ')
base_file_path = input('Путь к "базе" (не забывайте указывать расширение): ')
base_num_of_headers = int(input('Количество не считываемых строк в начале "базы" (хэдер, шапка таблицы и т.д.) [0|1|2|(...)]: '))

#Вводимый пользователем номер столбца - не индекс соответстующего элемента вложенного списка!
#Для преобразования в индекс надо будет вычесть 1.
base_pval_column = input('(Опционально) Номер столбца "базы" со значениями p-value [1|2|3|(...)|<enter>]: ')
if base_pval_column == '':
        base_pval_column, base_pval_threshold = None, None
else:
        base_pval_column = int(base_pval_column)
        base_pval_threshold = float(input('Верхний порог p-value (разделитель - точка)[5.00e-19|(...)]. P-VALUE ≤ '))

target_dir = input('Путь к папке для конечных файлов: ')

#Получение объёма оперативной памяти.
ram_size = get_ram_size(us_dir)

##Работа с "пользовательскими файлами" (содержащими запрашиваемые SNP).
##Предполагается, что наборы искомых SNP не настолько огромны,
##чтобы занимать больше 1/8 оперативной памяти.
##Поэтому они дробиться не будут.
##Идентификаторы SNP из каждого пользовательского
##файла будут искаться во всех фрагментах базы.
##Но если идентификатор уже найден в одном из фрагментов,
##то в следующих фрагментах он искаться не будет.
us_files = os.listdir(us_dir)
for us_file in us_files:
        print('Поиск в таблице ' + os.path.basename(base_file_path) + ' строк со снипами, взятыми из ' + us_file)
        search_res, us_rs_alr_found = [], set()
        with open(os.path.join(us_dir, us_file)) as us_op:

                #Ищем индекс refSNPID-содержащего столбца пользовательского файла.
                us_rs_col_index = rs_col_index_search(us_op)

                #Пользовательская таблица сразу, без дробления, преобразуется в двумерный массив.
                us_two_dim = list(csv.reader(us_op, delimiter = '\t'))

                #Удаление из пользовательской таблицы хэдера, если таковой имеется.
                if us_two_dim[0][0].find('#') != -1 or us_two_dim[0][0].find('track name') != -1:
                        us_two_dim = us_two_dim[1:]

                ##Работа с базой.
                with open(base_file_path) as base_op:

                        #Нахождение индекса refSNPID-столбца базы.
                        base_rs_col_index = rs_col_index_search(base_op)

                        #"Отделение" хэдеров от базы.
                        base_headers = header_save(base_op,
                                                   base_num_of_headers)
                        
                        #Переменная-стоппер, служащая сигналом завершения или продолжения дробления базы.
                        base_stop_reading = 'no'

                        #Формирование фрагментов базы и преобразование их в словари.
                        #Поиск строк базы, содержащих искомые refSNPID.
                        #Пополнение множества, в котором копятся уже найденные refSNPID,
                        #необходимого для предотвращения повторных поисков.
                        while base_stop_reading:
                                base_partial_two_dim, base_stop_reading = table_split(base_op,
                                                                                      base_rs_col_index,
                                                                                      base_pval_column,
                                                                                      base_pval_threshold,
                                                                                      ram_size,
                                                                                      base_stop_reading)
                                base_partial_dict = table_to_dict(base_partial_two_dim,
                                                                  base_rs_col_index)
                                partial_search_res, us_rs_alr_found = rs_search(us_two_dim,
                                                                                us_rs_col_index,
                                                                                base_partial_dict,
                                                                                us_rs_alr_found)

                                #Поскольку поиск производился во фрагментах базы,
                                #то и результаты будут поступать в отдельные двумерные массивы.
                                #Из них результаты добавляются в единый двумерный массив.
                                search_res += partial_search_res

                                #Выполнение цикла, в котором вызывается функция дробного считывания базы,
                                #прерывается после того, как переменная-стоппер в этой функции принимает соответствующее значение.
                                if base_stop_reading == 'yes':
                                        break

        #Сортировка по refSNPID-столбцу таблицы с результатами поиска SNP,
        #взятых из текущего пользовательского файла.
        #Сохранение результатов в файл.
        search_res.sort(key = lambda row: row[base_rs_col_index])
        target_file = us_file.split('.')[0] + '_I_' + os.path.basename(base_file_path.split('.txt')[0]) + '.txt'
        with open(os.path.join(target_dir, target_file), 'w') as target_file_op:
                if base_headers != []:
                        for line in base_headers:
                                target_file_op.write(line)
                for row in search_res:
                        target_file_op.write('\t'.join(row))

##Бонус: refSNPID-содержащие таблицы, созданные для тестирования
##с "базой" Whole_Blood_Analysis.perm.txt архива GTEx_Analysis_v6p_eQTL.
##Эта база небольшая, поэтому на современных компьютерах она вряд ли будет разбиваться.
##Чтобы с целью тестирования искусственно разбить небольшую базу,
##в условии "while source_file_op.tell() - init_mem_usage < ram_size // x" укажите такой x,
##чтобы неполное частное выражения ram_size // x было меньше размера базы в байтах.
##В целом, оттого, что вы выставляете разные значения x, результаты не должны меняться.
##В противном случае, немедленно составляйте баг-репорт в Issues!
'''
#refSNPID, встречающиеся в Whole_Blood_Analysis.perm 1 раз.
rs190889721
rs184276234
rs10910055
rs11122083
rs184383837

#refSNPID, повторяющиеся в Whole_Blood_Analysis.perm несколько раз + заведомо несуществующие refSNPID.
Дважды	rs1047712
Дважды	rs115477239
Трижды	rs1838150
Трижды	rs7159937
Пять_раз	rs4976210
Шесть_раз	rs67876192
Несуществующий	rs99999999999999999999
Несуществующий	rs55555555555555555555
Несуществующий	rs77777777777777777777
Несуществующий	rs22222222222222222222
Несуществующий	rs33333333333333333333

#refSNPID, встречающиеся 1 раз в Whole_Blood_Analysis.perm, но идущие не с первой строки.
1	q	!@#$%^&*()
2	w	)(*&^%$#@!
3	e	rs188678711
4	r	rs2203348
5	t	rs3760905
'''
