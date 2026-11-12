package com.v2ray.ang.service

import org.junit.Assert.*
import org.junit.Test

class PsiphonProxyPortRulesTest {
    @Test fun defaultsCanBeSavedWithBothPortsAutomaticallySelected() {
        assertEquals(PsiphonProxyPorts(0, 0), PsiphonProxyPortRules.parse("0", "0"))
        assertTrue(PsiphonProxyPortRules.isValid("0", "0"))
        assertTrue(PsiphonProxyPortRules.isValid(" 0 ", " 0 "))
    }

    @Test fun automaticAndDistinctManualPortsAreValid() {
        assertEquals(PsiphonProxyPorts(10810, 0), PsiphonProxyPortRules.parse("10810", "0"))
        assertEquals(PsiphonProxyPorts(0, 10811), PsiphonProxyPortRules.parse("0", "10811"))
        assertTrue(PsiphonProxyPortRules.isValid("65534", "65533"))
    }

    @Test fun malformedOrOutOfRangeValuesCannotBecomeAutomaticPorts() {
        for (value in listOf("", " ", "abc", "-1", "65535", "999999999999999999")) {
            assertFalse(value, PsiphonProxyPortRules.isValid(value, "0"))
        }
    }

    @Test fun reservedV2rayPortsAndEqualNonzeroPortsAreRejected() {
        assertFalse(PsiphonProxyPortRules.isValid("10808", "0"))
        assertFalse(PsiphonProxyPortRules.isValid("0", "10809"))
        assertFalse(PsiphonProxyPortRules.isValid("10810", "10810"))
    }
}
