<?xml version="1.0" encoding="UTF-8" ?>
<xsl:stylesheet version="1.0"
	xmlns="http://docbook.org/ns/docbook"
	xmlns:d="http://docbook.org/ns/docbook"
	xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
	xmlns:cc="http://creativecommons.org/ns#"
	xmlns:t="http://ns.crustytoothpaste.net/text-markup"
	xmlns:tr="http://ns.crustytoothpaste.net/troff"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	exclude-result-prefixes="t d">
	<xsl:output method="xml" encoding="UTF-8"/>

	<xsl:template match="t:root">
		<article version="5.0">
			<xsl:call-template name="info" />
			<xsl:apply-templates select="*"/>
		</article>
	</xsl:template>

	<xsl:template match="t:title"/>

	<xsl:template match="t:title" mode="info">
		<xsl:apply-templates select="node()"/>
	</xsl:template>

	<xsl:template match="t:section">
		<section>
			<xsl:call-template name="info" />
			<xsl:apply-templates select="*"/>
		</section>
	</xsl:template>

	<xsl:template match="t:inline[@type = 'emphasis']">
		<emphasis><xsl:apply-templates/></emphasis>
	</xsl:template>

	<xsl:template match="t:inline[@type = 'strong']">
		<emphasis role="strong"><xsl:apply-templates/></emphasis>
	</xsl:template>

	<xsl:template match="t:inline[@type = 'monospace']">
		<literal><xsl:apply-templates/></literal>
	</xsl:template>


	<xsl:template match="t:para">
		<para>
			<xsl:apply-templates/>
		</para>
	</xsl:template>

	<xsl:template match="t:para[count(node()) = 0]"/>

	<xsl:template name="info">
		<info>
			<title><xsl:apply-templates select="t:title" mode="info"/></title>
		</info>
	</xsl:template>

	<xsl:template name="process-bold">
		<xsl:choose>
			<xsl:when test="ancestor-or-self::*[@tr:font-weight][1][@tr:font-weight='bold']">
				<d:emphasis role="strong">
					<xsl:apply-templates/>
				</d:emphasis>
			</xsl:when>
			<xsl:otherwise>
				<xsl:apply-templates/>
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>

	<xsl:template name="process-italic">
		<xsl:choose>
			<xsl:when test="ancestor-or-self::*[@tr:font-variant][1][@tr:font-variant='italic']">
				<d:emphasis>
					<xsl:call-template name="process-bold"/>
				</d:emphasis>
			</xsl:when>
			<xsl:otherwise>
				<xsl:call-template name="process-bold"/>
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>

	<xsl:template match="tr:inline">
		<xsl:call-template name="process-italic"/>
	</xsl:template>

	<xsl:template match="tr:main|tr:block">
		<xsl:apply-templates/>
	</xsl:template>

	<xsl:template match="node()|@*">
		<xsl:copy>
			<xsl:apply-templates select="@*|node()"/>
		</xsl:copy>
	</xsl:template>
</xsl:stylesheet>
