#!/usr/bin/python

"""
Reliable Socket netstring implementation with start char recognition.

This syncs up on a tilde.
The tilde is followed by an eight digit decimal length for human readibilty.
The data that follows has the transmitted length after escaping.

The sockget(s) and socksend(s,data) are the main entry points.
These routines are guaranteed to receive and send whole records,
failing only on real occurences.  Real errors, time out and end of file
are distinguished.

The implementation relies on the underlying TCP/IP to live up to
the promise of reliable streaming - no further error checking is built in.

So the receive implementation will always return a well formed record, and
the send will send all of what is passed it.

It may be possible to miss a record, if the tilde used as start char is
not received for some reason - but the lower layers are supposed to
take care of that.

"""

import socket
import time


def sockget_len(s, L, data, run_during=None):
    """
    This fills a buffer of given length L from the socket s, recursively
    """
    if run_during != None:
        run_during()

    error = 0
    req_L = L - len(data)
    try:
        data += s.recv(req_L)
    except socket.error as msg:  # broken pipes again
        if 'timed out' in msg:
            rec = data + '2' * (L - len(data))
            return 2, rec  # time out
        print('socket error while receiving', msg)
        rec = data + '1' * (L - len(data))
        return 1, rec  # error = 1 is a snafu
    if not data:
        # print('end of file while receiving')
        rec = '0' * L
        return 3, rec  # This is end of file
    if len(data) != L:
        error, data = sockget_len(s, L, data)
    #   print 'sockget_len returning:',error,data
    return error, data


def sockget(s, run_during=None):
    """
    Gets a transmission from remote end, syncing on tilde,
    then gets 8 char length as string,
    then gets the data for the received length,
    then unescapes the data and returns it.
    relies on TCP/IP for error correction- no lrc used
    s - socket
    run_during - a function that gets run every time we try to get data from buffer
    """

    while True:  # Sync up on tilde
        tilde = b''
        error, tilde = sockget_len(s, 1, tilde, run_during)
        if error == 1:
            return error, ''  # Real error
        elif error == 2:
            return error, ''  # Time out
        elif error == 3:
            return error, ''  # End of file
        if tilde == b'~':
            break

    length = b''
    error, length = sockget_len(s, 8, length, run_during)  # get the length
    if error == 1:
        return error, ''  # real error
    elif error == 2:
        return error, ''  # Time out
    elif error == 3:
        return error, ''  # End of file
    L = int(length)
    buf = b''
    error, msg2 = sockget_len(s, L, buf, run_during)  # get the data

    if error == 0 and msg2:
        try:
            msg1 = msg2.replace('/\x81', '~')  # unescape the message
            msg = msg1.replace('/\xd0', '/')
        except TypeError:
            msg1 = msg2.replace(b'/\x81', b'~')  # unescape the message
            msg = msg1.replace(b'/\xd0', b'/')
    try:
        msg = msg.decode()  # try to turn back into string
    except:
        ahhdhaa = 0

    return error, msg  # error codes as above


def socksend(conn, msg):
    """
    Escapes, adds the length and start char, and sends the message off
    """

    try:
        msg1 = msg.replace('/', '/\xd0')
        msg2 = msg1.replace('~', '/\x81')
    except TypeError:
        msg1 = msg.replace(b'/', b'/\xd0')
        msg2 = msg1.replace(b'~', b'/\x81')
    length = '%08d' % len(msg2)  # max record length is 9999 ...
    try:
        msg2 = msg2.encode()  # make sure to send everything as bytes, not string
    except:
        adhhhhk = 0
    data = b'~' + length.encode() + msg2
    error, mess, rem = send_len(conn, data)
    return error, mess, rem  # 0 is no error, 1 is error


def send_len(s, data):
    """This recursively sends until all the data has been sent"""

    L = len(data)
    try:
        length_sent = s.send(data)
    except socket.error as err:
        mess = '[' + str(time.time()) + ']socket error on send: ' + str(err)
        print(mess)
        return 1, mess, L
    length_rem = L - length_sent
    if length_rem == 0:
        return 0, '0', 0
    else:
        data = data[length_sent:]
        error, mess, rem = send_len(s, data)
        if error == 0:
            return error, mess, rem
