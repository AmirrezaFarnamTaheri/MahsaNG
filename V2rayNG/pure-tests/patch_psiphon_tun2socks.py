"""Apply a fail-closed stop/start handshake to pinned Psiphon JNI source."""
from pathlib import Path
import sys


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Pinned native source differs from reviewed shutdown handshake")
    return text.replace(old, new, 1)


def harden_tun2socks(text):
    text = once(
        text,
        "static void terminateTun2SocksNative(\n",
        "static void prepareTun2SocksNative(\n"
        "        JNIEnv *env,\n"
        "        jclass cls);\n\n"
        "static void terminateTun2SocksNative(\n",
    )
    text = once(
        text,
        '        {"terminateTun2Socks", "()V", (void *) terminateTun2SocksNative},\n',
        '        {"prepareTun2Socks", "()V", (void *) prepareTun2SocksNative},\n'
        '        {"terminateTun2Socks", "()V", (void *) terminateTun2SocksNative},\n',
    )
    text = once(
        text,
        "    BLog_InitPsiphon();\n\n"
        "    __sync_bool_compare_and_swap(&g_terminate, 1, 0);\n\n"
        "    run();",
        "    BLog_InitPsiphon();\n\n"
        "    // The Kotlin start gate arms the one-shot worker before releasing\n"
        "    // the stop lock. Do not erase a stop that wins before JNI entry.\n"
        "    run();",
    )
    text = once(
        text,
        "\nvoid terminateTun2SocksNative(\n",
        "\nvoid prepareTun2SocksNative(\n"
        "        JNIEnv *env,\n"
        "        jclass cls) {\n"
        "    __sync_bool_compare_and_swap(&g_terminate, 1, 0);\n"
        "}\n\n"
        "void terminateTun2SocksNative(\n",
    )
    return text


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_psiphon_tun2socks.py pinned/tun2socks.c")
    path = Path(sys.argv[1])
    path.write_text(harden_tun2socks(path.read_text(encoding="utf-8")), encoding="utf-8")
