package com.v2ray.ang.util.dns

import org.junit.Assert.*
import org.junit.Test

class DnsWireTest {
    private fun response(type: DnsType = DnsType.A, flags: Int = 0x8180, rdata: ByteArray = byteArrayOf(203.toByte(),0,113,7)) : ByteArray {
        val query = DnsWire.query("www.example.com", type, 0x1234)
        val question = query.copyOfRange(12, query.size - 11)
        val header = byteArrayOf(0x12,0x34,(flags ushr 8).toByte(),flags.toByte(),0,1,0,1,0,0,0,0)
        val answer = byteArrayOf(0xc0.toByte(),0x0c,0,type.code.toByte(),0,1,0,0,0,60,0,rdata.size.toByte()) + rdata
        return header + question + answer
    }

    @Test fun decodesCompressedAWithTtlAndRecursionFlags() {
        val decoded = DnsWire.decode(response(), 0x1234)
        assertEquals("www.example.com", decoded.questionName)
        assertEquals(DnsType.A.code, decoded.questionType)
        assertEquals("203.0.113.7", decoded.records.single().value)
        assertEquals(60L, decoded.records.single().ttl)
        assertTrue(decoded.recursionAvailable)
        assertFalse(decoded.truncated)
    }

    @Test fun dnsErrorCodeIsNotConvertedIntoSuccessfulRecord() {
        val decoded = DnsWire.decode(response(flags = 0x8183), 0x1234)
        assertEquals(3, decoded.rcode)
    }

    @Test fun rejectsCompressionPointerLoopAndMismatchedId() {
        val loop = byteArrayOf(0x12,0x34,0x81.toByte(),0x80.toByte(),0,1,0,0,0,0,0,0,
            0xc0.toByte(),0x0c,0,1,0,1)
        val ex = assertThrows(DnsWireException::class.java) { DnsWire.decode(loop, 0x1234) }
        assertEquals("NAME_POINTER_LOOP", ex.code)
        assertEquals("TRANSACTION_MISMATCH", assertThrows(DnsWireException::class.java) {
            DnsWire.decode(response(), 0x4321)
        }.code)
    }

    @Test fun rejectsShortAnswerWithoutReadingBeyondPacket() {
        val data = response().dropLast(2).toByteArray()
        assertEquals("TRUNCATED_PACKET", assertThrows(DnsWireException::class.java) {
            DnsWire.decode(data, 0x1234)
        }.code)
    }

    @Test fun parsesTxtAndMxWithoutExposingRawBytes() {
        val txt = response(DnsType.TXT, rdata = byteArrayOf(2,'h'.code.toByte(),'i'.code.toByte()))
        assertEquals("hi", DnsWire.decode(txt, 0x1234).records.single().value)
        val mx = response(DnsType.MX, rdata = byteArrayOf(0,10,0xc0.toByte(),0x0c))
        assertEquals("10 www.example.com", DnsWire.decode(mx, 0x1234).records.single().value)
    }

    @Test fun validatesIdnaDomainAndRejectsOversizedLabel() {
        val unicode = DnsWire.query("bücher.example", DnsType.AAAA, 123)
        assertTrue(String(unicode, Charsets.ISO_8859_1).contains("xn--bcher-kva"))
        assertThrows(DnsWireException::class.java) { DnsWire.query("a".repeat(64) + ".com", DnsType.A, 123) }
    }

    @Test fun detectsTruncationBeforeParsingIncompleteAnswerSection() {
        val header = byteArrayOf(0x12,0x34,0x83.toByte(),0x80.toByte(),0,1,0,1,0,0,0,0)
        assertTrue(DnsWire.isTruncated(header, 0x1234))
    }
}
