<?xml version="1.0" encoding="UTF-8" ?>
<xsl:stylesheet version="1.0"
  xmlns="http://www.w3.org/1999/xhtml"
  xmlns:xh="http://www.w3.org/1999/xhtml"
	xmlns:tr="http://ns.crustytoothpaste.net/troff"
  xmlns:tm="http://ns.crustytoothpaste.net/text-markup"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	exclude-result-prefixes="xh tr tm xsl">
	<xsl:output method="xml" encoding="UTF-8"/>

	<xsl:template match="node()|@*">
		<xsl:copy>
			<xsl:apply-templates select="@*|node()"/>
		</xsl:copy>
	</xsl:template>

	<xsl:template match="tm:root">
		<html>
			<head>
				<title><xsl:apply-templates select="tm:title"/></title>
				<link rel="stylesheet" href="default.css"/>
			</head>
			<body>
				<xsl:call-template name="section"/>
			</body>
		</html>
	</xsl:template>

	<xsl:template match="tm:title">
		<xsl:apply-templates select=".//text()"/>
	</xsl:template>

	<xsl:template match="tm:para">
		<xsl:if test="string-length(normalize-space(.)) > 0">
			<p>
				<xsl:apply-templates/>
			</p>
		</xsl:if>
	</xsl:template>

	<xsl:template match="tm:inline">
		<xsl:variable name="tagname">
			<xsl:choose>
				<xsl:when test="@type='strong'">strong</xsl:when>
				<xsl:when test="@type='emphasis'">em</xsl:when>
				<xsl:when test="@type='quote'">q</xsl:when>
				<xsl:when test="@type='monospace'">tt</xsl:when>
				<xsl:when test="@type='superscript'">sup</xsl:when>
				<xsl:when test="@type='subscript'">sub</xsl:when>
				<xsl:otherwise>span</xsl:otherwise>
			</xsl:choose>
		</xsl:variable>
		<xsl:element namespace="http://www.w3.org/1999/xhtml" name="{$tagname}">
			<xsl:apply-templates/>
		</xsl:element>
	</xsl:template>

	<xsl:template match="tm:section" name="section">
		<xsl:variable name="level" select="count(ancestor-or-self::tm:section)+1"/>
		<div>
			<xsl:element namespace="http://www.w3.org/1999/xhtml" name="h{$level}">
				<xsl:apply-templates select="tm:title"/>
			</xsl:element>
			<xsl:apply-templates select="tm:*[local-name()!='title']"/>
		</div>
	</xsl:template>
</xsl:stylesheet>
