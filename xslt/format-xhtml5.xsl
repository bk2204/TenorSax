<?xml version="1.0" encoding="UTF-8" ?>
<xsl:stylesheet version="1.0"
	xmlns="http://www.w3.org/1999/xhtml"
	xmlns:xh="http://www.w3.org/1999/xhtml"
	xmlns:tr="http://ns.crustytoothpaste.net/troff"
	xmlns:tm="http://ns.crustytoothpaste.net/text-markup"
	xmlns:dc="http://purl.org/dc/elements/1.1/"
	xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	exclude-result-prefixes="xh tr tm xsl">
	<xsl:output method="xml" encoding="UTF-8"/>

	<xsl:template match="node()|@*">
		<xsl:copy>
			<xsl:apply-templates select="@*|node()"/>
		</xsl:copy>
	</xsl:template>

	<xsl:template match="node()|@*" mode="rdf"/>
	<xsl:template match="node()|@*" mode="body"/>

	<xsl:template match="tm:root">
		<html>
			<head>
				<title><xsl:apply-templates select="tm:title"/></title>
				<link rel="stylesheet" href="default.css"/>
				<xsl:apply-templates select="tm:meta"/>
			</head>
			<body class="article">
				<xsl:call-template name="body-header"/>
			</body>
		</html>
	</xsl:template>

	<xsl:template match="tm:meta">
		<xsl:if test="tm:generator">
			<meta name="generator">
				<xsl:attribute name="content">
					<xsl:value-of select="tm:generator/@name"/>
					<xsl:text> version </xsl:text>
					<xsl:value-of select="tm:generator/@version"/>
				</xsl:attribute>
			</meta>
		</xsl:if>
		<rdf:RDF>
			<rdf:Description rdf:about="">
				<xsl:apply-templates mode="rdf"/>
			</rdf:Description>
			<xsl:copy-of select="rdf:RDF/*"/>
		</rdf:RDF>
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

	<xsl:template match="tm:author" mode="raw">
		<xsl:apply-templates select="tm:firstname//text()"/>
		<xsl:if test="tm:middlename">
			<xsl:text> </xsl:text>
			<xsl:apply-templates select="tm:middlename//text()"/>
		</xsl:if>
		<xsl:if test="tm:lastname">
			<xsl:text> </xsl:text>
			<xsl:apply-templates select="tm:lastname//text()"/>
		</xsl:if>
	</xsl:template>

	<xsl:template match="tm:author" mode="rdf">
		<dc:creator><xsl:apply-templates select="." mode="raw"/></dc:creator>
	</xsl:template>

	<xsl:template match="tm:author" mode="body">
		<span xml:id="author">
			<xsl:apply-templates select="." mode="raw"/>
			<xsl:if test="tm:email">
				<xsl:text> </xsl:text>
				&lt;<xsl:apply-templates select="tm:email//text()"/>&gt;
			</xsl:if>
		</span>
		<br/>
	</xsl:template>

	<xsl:template name="body-header">
		<div xml:id="header">
			<h1><xsl:apply-templates select="tm:title"/></h1>
			<xsl:apply-templates select="/tm:root/tm:meta/*" mode="body"/>
		</div>
		<div xml:id="content">
			<xsl:apply-templates
				select="tm:*[local-name()!='title' and local-name()!='meta']"/>
		</div>
	</xsl:template>

	<xsl:template match="tm:section" name="section">
		<xsl:variable name="level" select="count(ancestor-or-self::tm:section)+1"/>
		<div>
			<xsl:element namespace="http://www.w3.org/1999/xhtml" name="h{$level}">
				<xsl:apply-templates select="tm:title"/>
			</xsl:element>
			<xsl:apply-templates
				select="tm:*[local-name()!='title' and local-name()!='meta']"/>
		</div>
	</xsl:template>
</xsl:stylesheet>
