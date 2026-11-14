package com.v2ray.ang.util

import com.google.gson.Gson
import com.v2ray.ang.dto.SubscriptionItem
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SubscriptionIndexDecoderTest {
    private val gson = Gson()

    @Test fun brokenJsonNullAndReadExceptionsDoNotHideHealthyGroups() {
        val goodOld = gson.toJson(SubscriptionItem("old", "https://example.invalid/a", addedTime = 1L))
        val goodNew = gson.toJson(SubscriptionItem("new", "https://example.invalid/b", addedTime = 3L))
        val records = linkedMapOf(
            "later" to goodNew,
            "broken" to "{",
            "null" to "null",
            "unreadable" to "not-used",
            "earlier" to goodOld,
        )
        val decoded = SubscriptionIndexDecoder.read(records.keys,
            readStoredJson = { key ->
                if (key == "unreadable") error("MMKV read failed")
                records[key]
            },
            parse = { json -> gson.fromJson(json, SubscriptionItem::class.java) },
        )
        assertEquals(listOf("earlier", "later"), decoded.map { it.first })
        assertEquals(listOf("old", "new"), decoded.map { it.second.remarks })
    }

    @Test fun emptyAndDuplicateKeysAreIgnoredAndEqualTimesUseStableKeyOrder() {
        val same = SubscriptionItem("same", addedTime = 9L)
        val result = SubscriptionIndexDecoder.read(
            listOf("z", "", "a", "z", "   ", "a"),
            readStoredJson = { gson.toJson(same) },
            parse = { gson.fromJson(it, SubscriptionItem::class.java) },
        )
        assertEquals(listOf("a", "z"), result.map { it.first })
    }

    @Test fun allInvalidItemsReturnEmptyListWithoutThrowing() {
        val values = listOf("{", "", "null")
        val result = SubscriptionIndexDecoder.read(values.indices.map(Int::toString),
            readStoredJson = { values[it.toInt()] },
            parse = { gson.fromJson(it, SubscriptionItem::class.java) },
        )
        assertTrue(result.isEmpty())
    }
}
