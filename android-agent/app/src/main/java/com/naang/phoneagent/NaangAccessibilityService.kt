package com.naang.phoneagent

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.graphics.Rect
import android.os.Bundle
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class NaangAccessibilityService : AccessibilityService() {
    companion object { @Volatile var instance: NaangAccessibilityService? = null }

    override fun onServiceConnected() {
        instance = this
        serviceInfo = serviceInfo.apply {
            flags = flags or AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
        }
    }

    override fun onDestroy() { if (instance === this) instance = null; super.onDestroy() }
    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() {}

    fun global(action: Int): Boolean = performGlobalAction(action)

    fun snapshot(): List<Map<String, Any?>> {
        val root = rootInActiveWindow ?: return emptyList()
        val out = mutableListOf<Map<String, Any?>>()
        walk(root, out, 0)
        root.recycle()
        return out
    }

    private fun walk(node: AccessibilityNodeInfo, out: MutableList<Map<String, Any?>>, depth: Int) {
        if (depth > 30 || out.size >= 2000) return
        val r = Rect(); node.getBoundsInScreen(r)
        out += mapOf(
            "class" to node.className?.toString(),
            "text" to node.text?.toString(),
            "contentDescription" to node.contentDescription?.toString(),
            "viewId" to node.viewIdResourceName,
            "clickable" to node.isClickable,
            "enabled" to node.isEnabled,
            "scrollable" to node.isScrollable,
            "bounds" to mapOf("left" to r.left, "top" to r.top, "right" to r.right, "bottom" to r.bottom)
        )
        for (i in 0 until node.childCount) node.getChild(i)?.let { child -> walk(child, out, depth + 1); child.recycle() }
    }

    fun clickByText(text: String): Boolean = find(rootInActiveWindow, text)?.performAction(AccessibilityNodeInfo.ACTION_CLICK) ?: false

    fun setText(text: String): Boolean {
        val node = find(rootInActiveWindow, null) ?: return false
        val args = Bundle().apply { putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text) }
        return node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
    }

    private fun find(node: AccessibilityNodeInfo?, text: String?): AccessibilityNodeInfo? {
        if (node == null) return null
        if (text == null || node.text?.toString() == text || node.contentDescription?.toString() == text) return node
        for (i in 0 until node.childCount) find(node.getChild(i), text)?.let { return it }
        return null
    }
}
