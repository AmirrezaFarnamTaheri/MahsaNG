package com.v2ray.ang.util

import com.google.gson.Gson
import com.v2ray.ang.dto.EConfigType
import com.v2ray.ang.dto.ServerConfig
import com.v2ray.ang.dto.V2rayConfig
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** Android-module regression: exercise real outbound DTOs and Gson, not handwritten JSON. */
class SubscriptionOutboundIdentityTest {
    private val outboundEncoder = Gson()

    private fun serverConfig(credential: String = "account-original",
                             sni: String = "original.example"): ServerConfig {
        val config = ServerConfig.create(EConfigType.VLESS)
        val outbound = requireNotNull(config.getProxyOutbound())
        val destination = requireNotNull(outbound.settings?.vnext).first()
        destination.address = "edge.example.org"
        destination.port = 443
        destination.users.first().id = credential
        val stream = requireNotNull(outbound.streamSettings)
        stream.security = V2rayConfig.TLS
        stream.tlsSettings = V2rayConfig.OutboundBean.StreamSettingsBean.TlsSettingsBean(serverName = sni)
        return config
    }

    /** Mirror the exact outbound serialization performed inside MmkvManager. */
    private fun sameIdentity(before: ServerConfig, after: ServerConfig): Boolean =
        SubscriptionReplacementPlan.matchesOutbound(
            before.getProxyOutbound()?.let { outboundEncoder.toJson(it) },
            after.getProxyOutbound()?.let { outboundEncoder.toJson(it) },
        )

    @Test fun changedCredentialsAndTlsDoNotRetargetSelectionAtSameEndpoint() {
        val original = serverConfig()
        val wrongAccount = serverConfig(credential = "account-other")
        val wrongTls = serverConfig(sni = "changed.example")
        val identical = serverConfig()

        assertEquals(original.getProxyOutbound()?.getServerAddress(),
            wrongAccount.getProxyOutbound()?.getServerAddress())
        assertEquals(original.getProxyOutbound()?.getServerPort(),
            wrongTls.getProxyOutbound()?.getServerPort())
        assertNotEquals(outboundEncoder.toJson(original.getProxyOutbound()),
            outboundEncoder.toJson(wrongAccount.getProxyOutbound()))
        assertNotEquals(outboundEncoder.toJson(original.getProxyOutbound()),
            outboundEncoder.toJson(wrongTls.getProxyOutbound()))

        val match = SubscriptionReplacementPlan.matchSelected(
            selectedGuid = "old",
            removedGuids = setOf("old"),
            selectedConfig = original,
            newConfigs = linkedMapOf(
                "wrong-account" to wrongAccount,
                "wrong-tls" to wrongTls,
                "same-account" to identical,
            ),
            sameEndpoint = ::sameIdentity,
        )
        assertEquals("same-account", match)
        assertNull(SubscriptionReplacementPlan.matchSelected(
            "old", setOf("old"), original,
            mapOf("wrong-account" to wrongAccount, "wrong-tls" to wrongTls),
            ::sameIdentity,
        ))
        assertFalse(sameIdentity(ServerConfig.create(EConfigType.CUSTOM),
            ServerConfig.create(EConfigType.CUSTOM)))
    }
}
