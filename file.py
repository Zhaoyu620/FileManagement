import logging
import os
from collections import OrderedDict

logging.basicConfig(level=logging.DEBUG)

# 磁盘块的数量和大小
BLOCK_NUM = 1000
BLOCK_SIZE = 10
# 保留区大小
RESERVED_SIZE = 20
# 文件描述符个数
FD_NUM = 10
# 文件分配到的磁盘块号数组的长度
FILE_BLOCK_ARRAY_SIZE = 3
# 文件夹名称
DIR_NAME = 'HOME'
# 内存块大小和内容
MEM_SIZE = 100
MEMORY = [str(i) for i in range(1, MEM_SIZE + 1)]
# 磁盘
DISK = [[0] * BLOCK_SIZE for i in range(BLOCK_NUM)]
# 位图
BIT_MAP = [0] * BLOCK_NUM
# 已生成的全部文件
CREATED_FILE = dict()
# 打开文件表,有序字典
OPEN_FILE_TABLE = OrderedDict()


# 文件类
class File(object):
    def __init__(self, fd, file_name, new=1):
        # 文件描述符，磁盘块号列表
        self.fd = fd
        self.file_name = file_name
        self.block_array = list()
        # 文件初始化即分配一个内存块
        if new:
            self.add_new_block()

    # 返回文件的第index块的内容
    def get_block(self, index):
        return self.block_array[index]

    # 关闭文件时刷新某一文件的内容
    def refresh_block(self, index, new_block):
        self.block_array[index] = new_block

    # 为文件添加新的磁盘块
    def add_new_block(self):
        # 寻找保留区后的第一个空闲块
        new_block_index = BIT_MAP[RESERVED_SIZE:].index(0) + RESERVED_SIZE
        logging.info(msg='为文件%s分配空闲块%d' % (self.file_name, new_block_index))
        BIT_MAP[new_block_index] = 1
        self.block_array.append(new_block_index)

    # 返回文件长度
    def get_file_length(self):
        if self.block_array:
            last_block_length = len([i for i in DISK[self.block_array[-1]] if i != 0])
            return last_block_length + BLOCK_SIZE * (len(self.block_array) - 1)
        else:
            return 0

    # 初始化文件，清空内容
    def initial(self):
        for i in self.block_array[1:]:
            BIT_MAP[i] = 0
            DISK[i] = [0] * 10
            logging.debug(msg='文件%s释放块%d' % (self.file_name, i))
        self.block_array = [self.block_array[0]]
        DISK[self.block_array[0]] = [0] * 10


# 目录类
class Directory(object):
    file_num = 0
    # 文件信息：文件描述符和文件描述符二元组列表
    file_fd_name = list()

    def __init__(self, fd, dir_name):
        self.name = dir_name
        self.fd = fd

    # 添加文件到文件夹中
    def add_file(self, fd, file_name):
        self.file_fd_name.append((fd, file_name))
        self.file_num += 1

    # 根据文件名删除文件,返回文件描述符
    def delete_file(self, file_name):
        fd = -1
        for f in self.file_fd_name:
            if f[1] == file_name:
                fd = f[0]
                target_file = CREATED_FILE[fd]
                for i in target_file.block_array:
                    BIT_MAP[i] = 0
                    DISK[i] = [0] * 10
                    logging.info(msg='释放内存块%d' % i)
                CREATED_FILE.pop(fd)
                self.file_fd_name.remove(f)
                logging.info(msg='删除文件%s' % file_name)
                self.file_num -= 1
                return fd
        if fd == -1:
            logging.info(msg='待删除文件名不存在于文件夹%s中' % self.name)

    # 依据文件名得到文件描述符
    def get_fd(self, file_name):
        fd = -1
        for f in self.file_fd_name:
            if f[1] == file_name:
                fd = f[0]
                self.file_num -= 1
                # 更新位图
                return fd
        if fd == -1:
            raise Exception(msg='待删除文件名不存在于文件夹%s中' % self.name)


# 文件描述符类
class FileDescriptor(object):
    def __init__(self, fd_num):
        self.fd_num = fd_num
        self.fd = [0] * fd_num

    # 返回未使用过的的文件描述符
    # 没有空闲的则返回-1
    def get_free_fd(self):
        for cnt, fd in enumerate(self.fd):
            if fd == 0:
                return cnt
        return -1

    # 使用文件或者目录对象指针代替
    # 文件描述符列表中对应位置的0
    def fd_allocate(self, fd, file):
        if fd < 0 or fd > self.fd_num - 1:
            raise ValueError(msg='文件描述符必须在0~%d之间' % (self.fd_num - 1))
        if self.fd[fd] != 0:
            raise Exception(msg='申请的文件描述符已被使用')

        self.fd[fd] = 1
        # 将文件保存到产生的文件中
        CREATED_FILE[fd] = file

    # 释放文件描述符
    def fd_release(self, fd):
        if fd < 0 or fd > self.fd_num - 1:
            raise ValueError(msg='文件描述符必须在0~%d之间' %
                                 (self.fd_num - 1))
        self.fd[fd] = 0
        logging.info(msg='释放文件描述符%d' % fd)


# 打开文件对象
class OpenFile(object):
    read_ptr = 0
    write_ptr = 0
    # 表示缓冲区当前存放的是文件的第几块内容
    block_ptr = 0
    # 读写互斥
    read_flag = 0
    write_flag = 0

    def __init__(self, fd):
        self.fd = fd
        self.file = CREATED_FILE[fd]
        self.buffer = [i for i in DISK[self.file.block_array[0]] if i != 0]

    # 将文件中的下一块的内容读到缓冲区中
    def buffer_next_block(self):
        self.block_ptr += 1
        self.buffer = DISK[self.file.block_array[self.block_ptr]]

    # 返回当前缓冲区存放的是文件内容的第几块
    def get_block_ptr(self):
        return self.block_ptr

    # 返回缓冲区内容
    def get_buffer(self):
        return self.buffer

    # 返回文件描述符
    def get_fd(self):
        return self.fd

    # 将缓冲区的内容写入文件相应块
    def dump_buffer(self):
        DISK[self.file.block_array[self.block_ptr]][0:len(self.buffer)] = self.buffer
        # 如果当前缓冲区是最后一块且已满，则再申请一块内容
        if self.block_ptr == len(self.file.block_array) - 1 and len(self.buffer) == BLOCK_SIZE:
            self.file.add_new_block()
            self.block_ptr += 1
            self.buffer = []

    # 在缓冲区中载入最后一块内存
    def buffer_tail_block(self):
        self.buffer = [i for i in DISK[self.file.block_array[-1]] if i != 0]
        self.block_ptr = len(self.file.block_array) - 1

    # 为读操作重新设置缓冲区内容
    def read_buffer(self):
        self.block_ptr = self.read_ptr // BLOCK_SIZE
        self.buffer = [i for i in DISK[self.file.block_array[self.block_ptr]] if i != 0]

    # 进入读状态
    def enter_read(self):
        if self.write_flag == 1:
            return False
        else:
            self.read_flag = 1
            return True

    # 进入写状态
    def enter_write(self):
        if self.read_flag == 1:
            return False
        else:
            self.write_flag = 1
            return True

"""""""""
IO系统
"""""""""
# 读取磁盘块的内容num个字节到内存
def read_block(block_data, mem_begin, num):
    if num + mem_begin > MEM_SIZE - 1:
        raise IOError('写入内存位置不当，没有足够位置存储')
    MEMORY[mem_begin:mem_begin + num] = block_data[0:num]
# 保存内存内容mem_begin开始num个字节到磁盘块，这里返回是交给打开文件的缓冲区处理
def write_block(mem_begin, num):
    if num + mem_begin > MEM_SIZE - 1:
        logging.info(msg='读取内存位置不当，没有足够字节内容')
        return 0
    return MEMORY[mem_begin:mem_begin + num]


# 将磁盘内容保存到文件中
def dump_disk():
    # 保存磁盘内容
    disk = ''
    for block in DISK:
        disk += '\t'.join([str(i) for i in block]) + '\n'
    with open('disk.txt', 'w')as f:
        f.write(disk)
    # 保存文件
    file_info = '',
    for fd, file in CREATED_FILE.items():
        if isinstance(file, File):
            file_info += str(fd) + ' ' + file.file_name + ' ' + \
                         ' '.join([str(i) for i in file.block_array]) + '\n'
    with open('file.txt', 'w') as f:
        f.write(file_info)
    logging.info(msg='将磁盘和文件保存到本地文件中')


# 将文件内容恢复到磁盘
def load_disk():
    # 恢复磁盘文件
    disk_file = 'disk.txt'
    file_file = 'file.txt'
    if disk_file in os.listdir('.') and file_file in os.listdir('.'):
        global DISK
        with open('disk.txt', 'r')as f:
            disk = [block.strip().split('\t') for block in f.readlines()]
        for cnt, block in enumerate(disk):
            DISK[cnt] = list(map(lambda x: int(x) if x == '0' else x, block))

        # 恢复创建的文件
        with open('file.txt', 'r')as f:
            file = [line.strip().split() for line in f.readlines()]
        CREATED_FILE[0] = directory
        for line in file:
            new_file = File(int(line[0]), line[1], new=0)
            new_file.block_array = [int(i) for i in line[2:]]
            for i in new_file.block_array:
                BIT_MAP[i] = 1
            file_descriptor.fd_allocate(int(line[0]), new_file)
            directory.add_file(int(line[0]), line[1])


"""""""""""""""
用户与文件系统接口
"""""""""""""""

# 根据文件名创建文件
def create(file_name):
    # 检查文件名是否存在
    if file_name in [f[1] for f in directory.file_fd_name]:
        logging.info(msg='文件名%s已存在,新建失败' % file_name)
        return 0
    free_fd = file_descriptor.get_free_fd()
    if free_fd == -1:
        logging.info(msg='没有空余的文件描述符可以使用')
        return 0
    new_file = File(free_fd, file_name)
    # 用新的文件替换原来文件描述符
    file_descriptor.fd_allocate(free_fd, new_file)
    directory.add_file(free_fd, file_name)
    logging.info(msg='文件%s新建成功，文件描述符为%d\n' % (file_name, free_fd))
    return 1


# 根据文件名删除文件
def destroy(file_name):
    fd = directory.delete_file(file_name)
    file_descriptor.fd_release(fd)


# 打开文件
def open_file(file_name):
    if file_name not in [f[1] for f in directory.file_fd_name]:
        logging.info(msg='文件%s不存在,无法打开' % file_name)
        return 0
    fd = directory.get_fd(file_name)
    file_opened = OpenFile(fd)
    OPEN_FILE_TABLE[fd] = file_opened
    logging.info(msg='成功打开文件%s' % file_name)
    return 1

# 关闭文件
def close_file(file_name):
    if file_name not in [f[1] for f in directory.file_fd_name]:
        logging.info(msg='文件%s不存在' % file_name)
        return 0
    fd = directory.get_fd(file_name)
    if fd not in OPEN_FILE_TABLE.keys():
        logging.info(msg='文件%s未打开' % file_name)
        return 0
    file_opened = OPEN_FILE_TABLE[fd]
    file_opened.dump_buffer()
    OPEN_FILE_TABLE.pop(fd)
    logging.info(msg='成功关闭文件%s' % file_name)


# 从指定文件读取num个字节到mem_begin开始的内存区中
def read(file_name, mem_begin, num):
    # 判断文件是否存在
    if file_name not in [f[1] for f in directory.file_fd_name]:
        logging.info(msg='文件%s不存在' % file_name)
        return 0
    # 判断文件是否打开
    fd = directory.get_fd(file_name)
    if fd not in OPEN_FILE_TABLE.keys():
        logging.info(msg='文件%s未打开,无法写' % file_name)
        return 0
    file_opened = OPEN_FILE_TABLE[fd]
    # 判断文件是否在写
    if not file_opened.enter_read():
        logging.info(msg='正在写文件，不可读')
        return 0
    file_length = file_opened.file.get_file_length()
    # 如果请求的大小超过了文件的长度则视为读取整个文件
    num = min(num, file_length)
    # 重新设置缓冲区
    file_opened.read_buffer()
    contents = []
    while num:
        # 读指针在当前缓冲区的位置
        buffer_read_pos = file_opened.read_ptr % BLOCK_SIZE
        if num + buffer_read_pos >= BLOCK_SIZE:
            read_block(file_opened.get_buffer()[buffer_read_pos:], mem_begin, BLOCK_SIZE - buffer_read_pos)
            contents += file_opened.get_buffer()[buffer_read_pos:]
            file_opened.buffer_next_block()
            num -= BLOCK_SIZE - buffer_read_pos
            file_opened.read_ptr += BLOCK_SIZE - buffer_read_pos
        elif 0 < num + buffer_read_pos < BLOCK_SIZE:
            read_block(file_opened.get_buffer()[buffer_read_pos:], mem_begin, num)
            contents += file_opened.get_buffer()[buffer_read_pos:buffer_read_pos + num]
            file_opened.read_ptr += num
            num = 0
    logging.debug(msg='读取文件%s信息%s' % (file_opened.file.file_name, ' '.join(contents)))


# 将内存数据添加到文件中,不覆盖原来的内容
def append(file_name, begin, num):
    # 判断文件是否存在
    if file_name not in [f[1] for f in directory.file_fd_name]:
        logging.info(msg='文件%s不存在' % file_name)
        return 0
    # 判断文件是否打开
    fd = directory.get_fd(file_name)
    if fd not in OPEN_FILE_TABLE.keys():
        logging.info(msg='文件%s未打开,无法写' % file_name)
        return 0
    file_opened = OPEN_FILE_TABLE[fd]
    # 判断文件是否在读
    if not file_opened.enter_write():
        logging.info(msg='正在读文件，不可写')
        return 0
    file_opened.write_ptr = file_opened.file.get_file_length()
    write_info = []
    while num:
        file_opened.buffer_tail_block()
        buffer = file_opened.get_buffer()
        if num + len(buffer) >= BLOCK_SIZE:
            write_size = BLOCK_SIZE - len(buffer)
            buffer += write_block(begin, write_size)
            write_info += buffer[-write_size:]
            num -= write_size
            begin += write_size
            file_opened.dump_buffer()
            file_opened.write_ptr += BLOCK_SIZE
        elif num + len(buffer) < BLOCK_SIZE:
            buffer += write_block(begin, num)
            write_info += buffer[-num:]
            num = 0
            begin += num
            file_opened.write_ptr += num
    logging.info(msg='向文件%s添加%s' % (file_name, ' '.join(write_info)))


# 将内存内容写入到文件中，覆盖原文件
def write(file_name, begin, num):
    # 判断文件是否存在
    if file_name not in [f[1] for f in directory.file_fd_name]:
        logging.info(msg='文件%s不存在' % file_name)
        return 0
    # 判断文件是否打开
    fd = directory.get_fd(file_name)
    if fd not in OPEN_FILE_TABLE.keys():
        logging.info(msg='文件%s未打开,无法写' % file_name)
        return 0
    file_opened = OPEN_FILE_TABLE[fd]
    # 判断文件是否在读
    if not file_opened.enter_write():
        logging.info(msg='正在读文件，不可写')
        return 0
    # 初始化文件
    if file_opened.file.get_file_length() != 0:
        file_opened.file.initial()
    write_info = []
    while num:
        file_opened.buffer_tail_block()
        buffer = file_opened.get_buffer()
        if num + len(buffer) >= BLOCK_SIZE:
            write_size = BLOCK_SIZE - len(buffer)
            buffer += write_block(begin, write_size)
            write_info += buffer[-write_size:]
            num -= write_size
            begin += write_size
            file_opened.dump_buffer()
            file_opened.write_ptr += BLOCK_SIZE
        elif num + len(buffer) < BLOCK_SIZE:
            buffer += write_block(begin, num)
            write_info += buffer[-num:]
            num = 0
            begin += num
            file_opened.write_ptr += num
    logging.info(msg='向文件%s写入%s' % (file_name, ' '.join(write_info)))


# 修改已打开文件的读写指针
def read_write_seek(file_name, pos):
    # 判断文件是否存在
    if file_name not in [f[1] for f in directory.file_fd_name]:
        logging.info(msg='文件%s不存在' % file_name)
        return 0
    # 判断文件是否打开
    fd = directory.get_fd(file_name)
    if fd not in OPEN_FILE_TABLE.keys():
        logging.info(msg='文件%s未打开,无法写' % file_name)
        return 0
    # 判断文件pos是否合法
    file_opened = OPEN_FILE_TABLE[fd]
    if pos < 0 or pos > file_opened.file.get_file_length() - 1:
        logging.info(msg='pos值必须在0~%d之间' % (file_opened.file.file_length - 1))

    file_opened.write_ptr = pos
    file_opened.read_ptr = pos


# 查看文件内容
def view_file(file_name):
    if file_name not in [f[1] for f in directory.file_fd_name]:
        logging.info(msg='文件%s不存在' % file_name)
        return 0
    fd = directory.get_fd(file_name)
    file = CREATED_FILE[fd]
    contents = []
    for block in file.block_array[:-1]:
        contents += DISK[block]
    contents += [i for i in DISK[file.block_array[-1]] if i != 0]
    logging.info(msg='文件%s的内容为%s' % (file_name, ' '.join([str(i) for i in contents])))


# 打印当前文件情况
def file_status():
    logging.info('*' * 30)
    # 打印文件夹和文件信息
    logging.info(msg='文件夹名称%s,文件描述符%d' % (directory.name, directory.fd))
    logging.info(msg='文件夹包含%d个文件' % len(directory.file_fd_name))
    for file_info in directory.file_fd_name:
        file = CREATED_FILE[int(file_info[0])]
        file_size = file.get_file_length()
        file_block_range = ' '.join([str(i) for i in file.block_array])
        logging.info(msg='文件描述符%s,文件名%s,文件大小%d个字节,占据磁盘块%s' %
                         (file_info[0], file_info[1], file_size, file_block_range))
    # 打印打开文件表信息
    logging.info(msg='打开的文件共%d个' % len(OPEN_FILE_TABLE))
    for fd, opened_file in OPEN_FILE_TABLE.items():
        file = CREATED_FILE[fd]
        file_size = file.get_file_length()
        file_block_range = ' '.join([str(i) for i in file.block_array])
        logging.info(msg='文件描述符%s,文件名%s,文件大小%d个字节,占据磁盘块%s' %
                         (file_info[0], file_info[1], file_size, file_block_range))
    logging.info('*' * 30 + '\n')


# 新建文件描述符实例
file_descriptor = FileDescriptor(FD_NUM)
# 新建文件夹
directory = Directory(0, DIR_NAME)
file_descriptor.fd_allocate(0, directory)
logging.info(msg='文件夹%s新建成功，文件描述符为%d' % (DIR_NAME, 0))


