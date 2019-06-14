from file import *


# 菜单驱动程序
def menu_drive():
    file_status()
    while True:
        logging.info(msg='\n(1)新建文件(2)编辑文件(3)查看文件\n'
                         '(4)删除文件(5)退出程序')
        while True:
            try:
                choose = int(input())
                break
            except ValueError as e:
                logging.debug(msg=e)
        # 新建文件
        if choose == 1:
            logging.info(msg='请输入文件名')
            file_name = input()
            create(file_name)
        # 编辑文件
        elif choose == 2:
            while True:
                logging.info(msg='请输入文件名')
                file_name = input()
                if open_file(file_name):
                    break
            while True:
                logging.info(msg='\n(1)重写文件(2)续写文件(3)读取文件\n'
                                 '(4)查看文件(5)移动指针(6)退出编辑')
                while True:
                    try:
                        choose = int(input())
                        break
                    except ValueError as e:
                        logging.debug(msg=e)
                # 重写文件
                if choose == 1:
                    logging.info(msg='请输入内存起始地址，字节数')
                    while True:
                        try:
                            begin, num = input().split(' ')
                            if isinstance(int(begin), int) and isinstance(int(num), int):
                                break
                        except Exception as e:
                            logging.info(msg=e)
                    write(file_name, int(begin), int(num))
                # 续写文件
                elif choose == 2:
                    logging.info(msg='请输入内存起始地址，字节数')
                    while True:
                        try:
                            begin, num = input().split(' ')
                            if isinstance(int(begin), int) and isinstance(int(num), int):
                                break
                        except Exception as e:
                            logging.info(msg=e)
                    append(file_name, int(begin), int(num))
                # 读取文件
                elif choose == 3:
                    logging.info(msg='请输入内存起始地址，字节数')
                    while True:
                        try:
                            begin, num = input().split(' ')
                            if isinstance(int(begin), int) and isinstance(int(num), int):
                                break
                        except Exception as e:
                            logging.info(msg=e)
                    read(file_name, int(begin), int(num))
                # 查看文件内容
                elif choose == 4:
                    view_file(file_name)
                # 移动文件指针
                elif choose == 5:
                    logging.info(msg='请输入文件指针新值')
                    while True:
                        try:
                            pos = input()
                            if isinstance(int(pos), int):
                                break
                        except Exception as e:
                            logging.info(msg=e)
                    read_write_seek(file_name, int(pos))
                # 退出编辑
                elif choose == 6:
                    close_file(file_name)
                    break
        # 查看文件内容
        elif choose == 3:
            logging.info(msg='请输入文件名')
            file_name = input()
            view_file(file_name)
        # 删除文件
        elif choose == 4:
            logging.info(msg='请输入文件名')
            file_name = input()
            destroy(file_name)
        # 结束程序
        elif choose == 5:
            logging.info(msg='文件操作执行完毕')
            break
        else:
            logging.info(msg='输入选项无效')
        file_status()

if __name__ == '__main__':
    load_disk()
    menu_drive()
    dump_disk()