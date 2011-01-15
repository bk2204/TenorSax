<?xml version="1.0" encoding="UTF-8" ?>
<xsl:stylesheet version="1.0"
	xmlns="http://www.w3.org/1999/XSL/Format"
	xmlns:t="http://ns.crustytoothpaste.net/troff"
	xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output method="xml" encoding="UTF-8"/>

	<xsl:template name="set-default-attributes">
		<xsl:attribute name="font-size">10pt</xsl:attribute>
		<xsl:attribute name="font-family">Times,serif</xsl:attribute>
	</xsl:template>

	<!-- FIXME: allow customization for at least A4 -->
	<xsl:template match="/">
		<root>
			<layout-master-set>
				<simple-page-master master-name="default" page-width="8.5in"
					page-height="11in" margin-top="0.5in" margin-bottom="0.5in"
					margin-left="1in" margin-right="1in">
					<region-body margin-bottom="0.5in" margin-top="0.5in" column-gap="12pt" column-count="1"/>
					<region-before region-name="xsl-region-before-first" extent="0.4in" display-align="before"/>
					<region-after region-name="xsl-region-after-first" extent="0.4in" display-align="after"/>
				</simple-page-master>
				<page-sequence-master master-name="body">
					<repeatable-page-master-alternatives>
						<conditional-page-master-reference master-reference="default"/>
					</repeatable-page-master-alternatives>
				</page-sequence-master>
			</layout-master-set>
			<declarations>
				<xsl:copy-of select="rdf:RDF"/>
			</declarations>
			<page-sequence master-reference="body">
				<xsl:apply-templates select="t:title"/>
				<xsl:apply-templates select="t:main"/>
			</page-sequence>
		</root>
	</xsl:template>

	<xsl:template match="t:title">
		<title><xsl:apply-templates select="node()"/></title>
	</xsl:template>

	<xsl:template match="t:main">
		<flow flow-name="xsl-region-body">
			<block>
				<xsl:call-template name="set-default-attributes"/>
				<xsl:apply-templates/>
			</block>
		</flow>
	</xsl:template>

	<xsl:template match="t:block">
		<xsl:apply-templates/>
	</xsl:template>

	<xsl:template match="t:inline">
		<xsl:apply-templates/>
	</xsl:template>

	<xsl:template match="t:*">
		<xsl:message terminate="yes">Found unknown element <xsl:value-of select="name(.)"/></xsl:message>
	</xsl:template>
</xsl:stylesheet>
