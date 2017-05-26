#!/usr/bin/env python2

# This file is part of Archivematica.
#
# Copyright 2010-2017 Artefactual Systems Inc. <http://artefactual.com>
#
# Archivematica is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Archivematica is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Archivematica.  If not, see <http://www.gnu.org/licenses/>.

# @package Archivematica
# @subpackage archivematicaClientScript
# @author Joseph Perry <joseph@artefactual.com>
from __future__ import print_function
import re
import os
from lxml import etree as etree
import sys
import traceback
import uuid
import string
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta

import django
django.setup()
# dashboard
from main.models import RightsStatement, RightsStatementOtherRightsInformation, RightsStatementOtherRightsDocumentationIdentifier, RightsStatementRightsGranted, RightsStatementRightsGrantedNote, RightsStatementRightsGrantedRestriction

# archivematicaCommon
from fileOperations import getFileUUIDLike
import databaseFunctions

while False:
    import time
    time.sleep(10)

transferUUID = sys.argv[1]
transferName = sys.argv[2]
transferPath = sys.argv[3]
date = sys.argv[4]

currentDirectory = ""
exitCode = 0

def callWithException(exception):
    traceback

def getTimedeltaFromRetensionSchedule(RetentionSchedule):
    ret = 0
    rs = ["0"]
    rss = RetentionSchedule.split(".")
    for part in rss:
        entry = "0"
        for c in part:
            if c in string.digits:
                entry = "%s%s" % (entry, c)
        rs.append(entry)
    for entry in rs:
        ret += int (entry)

    ret = relativedelta(years=ret)
    return ret


def getDateTimeFromDateClosed(dateClosed):
    i = 19 #the + or minus for offset (DST + timezone)
    if dateClosed== None:
        return

    dateClosedDT = datetime.strptime(dateClosed[:i], '%Y-%m-%dT%H:%M:%S')
    print(dateClosedDT)
    offSet = dateClosed[i+1:].split(":")
    offSetTD = timedelta(hours=int(offSet[0]), minutes=int(offSet[1]))

    if dateClosed[i] == "-":
        dateClosedDT = dateClosedDT - offSetTD
    elif  dateClosed[i] == "+":
        dateClosedDT = dateClosedDT + offSetTD
    else:
        print("Error with offset in:", dateClosed, file=sys.stderr)
        return dateClosedDT
    return dateClosedDT

for dir in os.listdir(transferPath):
    dirPath = os.path.join(transferPath, dir)
    if not os.path.isdir(dirPath):
        continue

    xmlFilePath = os.path.join(dirPath, "ContainerMetadata.xml")
    try:
        tree = etree.parse(xmlFilePath)
        root = tree.getroot()
    except:
        print("Error parsing: ", xmlFilePath.replace(transferPath, "%transferDirectory%", 1), file=sys.stderr)
        exitCode += 1
        continue
    try:
        RetentionSchedule = root.find("Container/RetentionSchedule").text
        DateClosed = root.find("Container/DateClosed").text
    except:
        print("Error retrieving values from: ", xmlFilePath.replace(transferPath, "%transferDirectory%", 1), file=sys.stderr)
        exitCode += 1
        continue

    retentionPeriod = getTimedeltaFromRetensionSchedule(RetentionSchedule)
    startTime = getDateTimeFromDateClosed(DateClosed)
    endTime = startTime + retentionPeriod

    # make end time end of year
    endTimeEndOfYearDiff = datetime(endTime.year, 12, 31) - endTime
    endTime = endTime + endTimeEndOfYearDiff


    indexForOnlyDate = 10
    startTime = startTime.__str__()[:indexForOnlyDate]
    endTime = endTime.__str__()[:indexForOnlyDate]

    for file in os.listdir(dirPath):
        filePath = os.path.join(dirPath, file)
        if  file == "ContainerMetadata.xml" or file.endswith("Metadata.xml") or not os.path.isfile(filePath):
            continue

        fileUUID = getFileUUIDLike(filePath, transferPath, transferUUID, "transfer", "%transferDirectory%")[filePath.replace(transferPath, "%transferDirectory%", 1)]
        FileMetadataAppliesToType = '7f04d9d4-92c2-44a5-93dc-b7bfdf0c1f17'

        # RightsStatement
        statement = RightsStatement.objects.create(
            metadataappliestotype_id=FileMetadataAppliesToType,
            metadataappliestoidentifier=fileUUID,
            rightsstatementidentifiertype="UUID",
            rightsstatementidentifiervalue=str(uuid.uuid4()),
            rightsholder=1,
            rightsbasis="Other"
        )

        # RightsStatementOtherRightsInformation
        info = RightsStatementOtherRightsInformation.objects.create(
           rightsstatement=statement,
           otherrightsbasis="Policy"
        )

        # RightsStatementOtherRightsDocumentationIdentifier
        identifier = RightsStatementOtherRightsDocumentationIdentifier.objects.create(
            rightsstatementotherrights=info
        )

        # RightsStatementRightsGranted
        granted = RightsStatementRightsGranted.objects.create(
            rightsstatement=statement,
            act="Disseminate",
            startdate=startTime,
            enddate=endTime
        )

        # RightsStatementRightsGrantedNote
        RightsStatementRightsGrantedNote.objects.create(
            rightsgranted=granted,
            rightsgrantednote="Closed until " + endTime
        )

        # RightsStatementRightsGrantedRestriction
        RightsStatementRightsGrantedRestriction.objects.create(
            rightsgranted=granted,
            restriction="Disallow"
        )

quit(exitCode)
