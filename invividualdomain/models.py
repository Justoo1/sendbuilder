from django.db import models
from builder.models import Study


class CLDomainData(models.Model):
    """Model for Clinical Observations (CL) domain data"""
    # Required CDISC CL variables
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)  # Study Identifier
    domain = models.CharField(max_length=2, default='CL')  # Domain Abbreviation
    usubjid = models.CharField(max_length=64)  # Unique Subject Identifier
    clseq = models.IntegerField()  # Sequence Number
    cltestcd = models.CharField(max_length=8)  # Clinical Observation Test Short Name
    cltest = models.CharField(max_length=40)  # Clinical Observation Test Name
    clorres = models.CharField(max_length=200, blank=True)  # Result or Finding in Original Units
    clorresu = models.CharField(max_length=8, blank=True)  # Original Units
    clstresc = models.CharField(max_length=200, blank=True)  # Character Result/Finding in Std Format
    clstresn = models.FloatField(null=True, blank=True)  # Numeric Result/Finding in Standard Units
    clstresu = models.CharField(max_length=8, blank=True)  # Standard Units
    clstat = models.CharField(max_length=8, blank=True)  # Completion Status
    clreasnd = models.CharField(max_length=200, blank=True)  # Reason Not Done
    clnam = models.CharField(max_length=200, blank=True)  # Vendor Name
    clspec = models.CharField(max_length=200, blank=True)  # Specimen Material Type
    clantreg = models.CharField(max_length=8, blank=True)  # Anatomical Region
    cllat = models.CharField(max_length=8, blank=True)  # Laterality
    cldir = models.CharField(max_length=8, blank=True)  # Directionality
    clportot = models.CharField(max_length=8, blank=True)  # Portion or Totality
    clmethod = models.CharField(max_length=200, blank=True)  # Method of Test
    cluschfl = models.CharField(max_length=1, blank=True)  # Unscheduled Flag
    clblfl = models.CharField(max_length=1, blank=True)  # Baseline Flag
    cldrvfl = models.CharField(max_length=1, blank=True)  # Derived Flag
    cleval = models.CharField(max_length=40, blank=True)  # Evaluator
    cleltmle = models.CharField(max_length=8, blank=True)  # Planned Time Point Name
    cltptnum = models.FloatField(null=True, blank=True)  # Planned Time Point Number
    cleltm = models.CharField(max_length=8, blank=True)  # Planned Elapsed Time from Time Point Ref
    cltptref = models.CharField(max_length=40, blank=True)  # Time Point Reference
    clrftdtc = models.CharField(max_length=20, blank=True)  # Date/Time of Reference Time Point
    
    # Timing variables
    cldtc = models.CharField(max_length=20, blank=True)  # Date/Time of Clinical Observation
    cldy = models.IntegerField(null=True, blank=True)  # Study Day of Clinical Observation
    cltm = models.CharField(max_length=8, blank=True)  # Time of Clinical Observation
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['domain', 'usubjid', 'clseq']
        verbose_name = 'Clinical Observations (CL) domain data'
        verbose_name_plural = 'Clinical Observations (CL) domain data'
    
    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
        
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)
    

class DMDomainData(models.Model):
    """Model for Demographics (DM) domain data"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='DM')
    usubjid = models.CharField(max_length=64, unique=True)
    subjid = models.CharField(max_length=64)  # Subject ID for the Study
    rfstdtc = models.CharField(max_length=20, blank=True)  # Subject Reference Start Date/Time
    rfendtc = models.CharField(max_length=20, blank=True)  # Subject Reference End Date/Time
    siteid = models.CharField(max_length=20, blank=True)  # Study Site Identifier
    sex = models.CharField(max_length=8, blank=True)
    race = models.CharField(max_length=40, blank=True)
    age = models.IntegerField(null=True, blank=True)
    ageu = models.CharField(max_length=8, blank=True)  # Age Units
    arm = models.CharField(max_length=64, blank=True)
    armcd = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=40, blank=True)

    class Meta:
        verbose_name = 'Demographics (DM) domain data'
        verbose_name_plural = 'Demographics (DM) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)

class DSDomainData(models.Model):
    """Model for Disposition (DS) domain data"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='DS')
    usubjid = models.CharField(max_length=64)
    dsseq = models.IntegerField()
    dsgrpid = models.CharField(max_length=40, blank=True)
    dsspid = models.CharField(max_length=40, blank=True)
    dsterm = models.CharField(max_length=200)
    dsdecod = models.CharField(max_length=200)
    dsstdtc = models.CharField(max_length=20, blank=True)
    dsstresc = models.CharField(max_length=200, blank=True)
    epoch = models.CharField(max_length=40, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'dsseq']
        verbose_name = 'Disposition (DS) domain data'
        verbose_name_plural = 'Disposition (DS) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)


class EXDomainData(models.Model):
    """Model for Exposure (EX) domain data"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='EX')
    usubjid = models.CharField(max_length=64)
    exseq = models.IntegerField()
    extrt = models.CharField(max_length=100)  # Name of Treatment
    exdose = models.FloatField(null=True, blank=True)
    exdosu = models.CharField(max_length=40, blank=True)
    exdosfrm = models.CharField(max_length=40, blank=True)
    exdosfrq = models.CharField(max_length=40, blank=True)
    exroute = models.CharField(max_length=40, blank=True)
    exstdtc = models.CharField(max_length=20, blank=True)
    extendtc = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'exseq']
        verbose_name = 'Exposure (EX) domain data'
        verbose_name_plural = 'Exposure (EX) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)


class LBDomainData(models.Model):
    """Model for Laboratory (LB) domain data"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='LB')
    usubjid = models.CharField(max_length=64)
    lbseq = models.IntegerField()
    lbtestcd = models.CharField(max_length=8)
    lbtest = models.CharField(max_length=40)
    lborres = models.CharField(max_length=200, blank=True)
    lborresu = models.CharField(max_length=8, blank=True)
    lbstresc = models.CharField(max_length=200, blank=True)
    lbstresn = models.FloatField(null=True, blank=True)
    lbstresu = models.CharField(max_length=8, blank=True)
    lblow = models.FloatField(null=True, blank=True)
    lbhigh = models.FloatField(null=True, blank=True)
    lblstfl = models.CharField(max_length=1, blank=True)
    lbnrind = models.CharField(max_length=8, blank=True)
    lbtpt = models.CharField(max_length=40, blank=True)
    lbtptnum = models.FloatField(null=True, blank=True)
    lbdtc = models.CharField(max_length=20, blank=True)
    lbdy = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'lbseq']
        verbose_name = 'Laboratory (LB) domain data'
        verbose_name_plural = 'Laboratory (LB) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)


class VSDomainData(models.Model):
    """Model for Vital Signs (VS) domain data"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='VS')
    usubjid = models.CharField(max_length=64)
    vsseq = models.IntegerField()
    vstestcd = models.CharField(max_length=8)
    vstest = models.CharField(max_length=40)
    vsorres = models.CharField(max_length=200, blank=True)
    vsorresu = models.CharField(max_length=8, blank=True)
    vsstresc = models.CharField(max_length=200, blank=True)
    vsstresn = models.FloatField(null=True, blank=True)
    vsstresu = models.CharField(max_length=8, blank=True)
    vsdtc = models.CharField(max_length=20, blank=True)
    vsdy = models.IntegerField(null=True, blank=True)
    vstpt = models.CharField(max_length=40, blank=True)
    vstptnum = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'vsseq']
        verbose_name = 'Vital Signs (VS) domain data'
        verbose_name_plural = 'Vital Signs (VS) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)


class BWDomainData(models.Model):
    """Model for Body Weights (BW) domain data"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='BW')
    usubjid = models.CharField(max_length=64)
    bwseq = models.IntegerField()
    bwtestcd = models.CharField(max_length=8, default='BODYWT')
    bwtest = models.CharField(max_length=40, default='Body Weight')
    bworres = models.FloatField(null=True, blank=True)
    bworresu = models.CharField(max_length=8, blank=True)
    bwstresc = models.CharField(max_length=200, blank=True)
    bwstresn = models.FloatField(null=True, blank=True)
    bwstresu = models.CharField(max_length=8, blank=True)
    bwdtc = models.CharField(max_length=20, blank=True)
    bwdy = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'bwseq']
        verbose_name = 'Body Weights (BW) domain data'
        verbose_name_plural = 'Body Weights (BW) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)


class FCDomainData(models.Model):
    """Model for Food Consumption (FC) domain data"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='FC')
    usubjid = models.CharField(max_length=64)
    fcseq = models.IntegerField()
    fctestcd = models.CharField(max_length=8)
    fctest = models.CharField(max_length=40)
    fcorres = models.FloatField(null=True, blank=True)
    fcorresu = models.CharField(max_length=8, blank=True)
    fcdtc = models.CharField(max_length=20, blank=True)
    fcdy = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'fcseq']
        verbose_name = 'Food Consumption (FC) domain data'
        verbose_name_plural = 'Food Consumption (FC) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)

class TADomainData(models.Model):
    """Model for Test Article (TA) domain data"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='TA')
    taid = models.CharField(max_length=40)  # Test Article Identifier
    tatrt = models.CharField(max_length=100)  # Test Article Name
    taadm = models.CharField(max_length=40)  # Route of Administration
    taform = models.CharField(max_length=40, blank=True)  # Dosage Form
    taunit = models.CharField(max_length=8, blank=True)  # Units
    taadj = models.CharField(max_length=20, blank=True)  # Adjustment Type
    taadjval = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = 'Test Article (TA) domain data'
        verbose_name_plural = 'Test Article (TA) domain data'

    def __str__(self):
        return f"{self.domain}-{self.taid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)

class TSDomainData(models.Model):
    """Model for Trial Summary (TS) domain data"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='TS')
    tsseq = models.IntegerField()
    tstestcd = models.CharField(max_length=8)  # Trial Summary Parameter Short Name
    tstest = models.CharField(max_length=40)  # Trial Summary Parameter
    tsval = models.CharField(max_length=200)  # Parameter Value
    tsvaldn = models.CharField(max_length=200, blank=True)  # Value for Controlled Terminology
    tsdtype = models.CharField(max_length=20, blank=True)  # Type of Value

    class Meta:
        unique_together = ['domain', 'studyid', 'tsseq']
        verbose_name = 'Trial Summary (TS) domain data'
        verbose_name_plural = 'Trial Summary (TS) domain data'

    def __str__(self):
        return f"{self.domain}-{self.studyid}-{self.tstestcd}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)

class RELRECDomainData(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    rdomain = models.CharField(max_length=2)  # Related Domain Abbreviation
    usubjid = models.CharField(max_length=64, blank=True)
    idvar = models.CharField(max_length=40)  # Identifier Variable
    idvarval = models.CharField(max_length=64)  # Identifier Value
    relgrp = models.CharField(max_length=40)  # Relationship Group Identifier
    relid = models.CharField(max_length=40, blank=True)  # Relationship ID

    class Meta:
        verbose_name = 'Related Records (RELREC) domain data'
        verbose_name_plural = 'Related Records (RELREC) domain data'

    def __str__(self):
        return f"{self.relgpr} - {self.rdomain} - {self.idvar}"

class REDomainData(models.Model):
    """Model for Reproductive Evaluation (RE) domain data"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='RE')
    usubjid = models.CharField(max_length=64)
    reseq = models.IntegerField()
    retestcd = models.CharField(max_length=8)
    retest = models.CharField(max_length=40)
    reorres = models.CharField(max_length=200, blank=True)
    restresc = models.CharField(max_length=200, blank=True)
    restresn = models.FloatField(null=True, blank=True)
    redtc = models.CharField(max_length=20, blank=True)
    redy = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'reseq']
        verbose_name = 'Reproductive Evaluation (RE) domain data'
        verbose_name_plural = 'Reproductive Evaluation (RE) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)

class MIDomainData(models.Model):
    """Model for Microscopic Findings (MI) domain data"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='MI')
    usubjid = models.CharField(max_length=64)
    miseq = models.IntegerField()
    milat = models.CharField(max_length=8, blank=True)
    mitestcd = models.CharField(max_length=8)
    mitest = models.CharField(max_length=40)
    miorres = models.CharField(max_length=200, blank=True)
    mispec = models.CharField(max_length=200, blank=True)
    midae = models.CharField(max_length=1, blank=True)  # Death association flag
    midtc = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'miseq']
        verbose_name = 'Microscopic Findings (MI) domain data'
        verbose_name_plural = 'Microscopic Findings (MI) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)

class MADomainData(models.Model):
    """Model for Macroscopic Observations (MA) domain data"""
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='MA')
    usubjid = models.CharField(max_length=64)
    maseq = models.IntegerField()
    matestcd = models.CharField(max_length=8)
    matest = models.CharField(max_length=40)
    maorres = models.CharField(max_length=200, blank=True)
    maspec = models.CharField(max_length=200, blank=True)
    madtc = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'maseq']
        verbose_name = 'Macroscopic Observations (MA) domain data'
        verbose_name_plural = 'Macroscopic Observations (MA) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)

# 2. Protocol Deviations (DV)
class DVDomainData(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='DV')
    usubjid = models.CharField(max_length=64)
    dvseq = models.IntegerField()
    dvterm = models.CharField(max_length=200)
    dvcat = models.CharField(max_length=200, blank=True)
    dvdecod = models.CharField(max_length=200, blank=True)
    dvstdtc = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'dvseq']
        verbose_name = 'Protocol Deviations (DV) domain data'
        verbose_name_plural = 'Protocol Deviations (DV) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)

# 3. Concomitant Medications (CM)
class CMDomainData(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='CM')
    usubjid = models.CharField(max_length=64)
    cmseq = models.IntegerField()
    cmtrt = models.CharField(max_length=200)
    cmdecod = models.CharField(max_length=200, blank=True)
    cmstdtc = models.CharField(max_length=20, blank=True)
    cmmodify = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'cmseq']
        verbose_name = 'Concomitant Medications (CM) domain data'
        verbose_name_plural = 'Concomitant Medications (CM) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)

# 5. Trial Visits (TV)
class TVDomainData(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='TV')
    visitnum = models.FloatField()
    visit = models.CharField(max_length=40)
    armcd = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ['domain', 'visitnum']
        verbose_name = 'Trial Visits (TV) domain data'
        verbose_name_plural = 'Trial Visits (TV) domain data'

    def __str__(self):
        return f"{self.domain}-{self.visitnum}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)

# 6. Trial Elements (TE)
class TEDomainData(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='TE')
    etseq = models.IntegerField()
    etcd = models.CharField(max_length=8)
    etdecod = models.CharField(max_length=200)
    etduru = models.CharField(max_length=10)

    class Meta:
        unique_together = ['domain', 'etseq']
        verbose_name = 'Trial Elements (TE) domain data'
        verbose_name_plural = 'Trial Elements (TE) domain data'

    def __str__(self):
        return f"{self.domain}-{self.etseq}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)

# 7. Functional Observational Battery (FA)
class FADomainData(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='FA')
    usubjid = models.CharField(max_length=64)
    faseq = models.IntegerField()
    fatestcd = models.CharField(max_length=8)
    fatest = models.CharField(max_length=40)
    faorres = models.CharField(max_length=200, blank=True)
    fastresc = models.CharField(max_length=200, blank=True)
    fastresn = models.FloatField(null=True, blank=True)
    fastresu = models.CharField(max_length=8, blank=True)
    fadtc = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'faseq']
        verbose_name = 'Functional Observational Battery (FA) domain data'
        verbose_name_plural = 'Functional Observational Battery (FA) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)

# 8. Palpable Mass (PW)
class PWDomainData(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='PW')
    usubjid = models.CharField(max_length=64)
    pwseq = models.IntegerField()
    pwtestcd = models.CharField(max_length=8)
    pwtest = models.CharField(max_length=40)
    pworres = models.CharField(max_length=200, blank=True)
    pwspec = models.CharField(max_length=200, blank=True)
    pwdtc = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'pwseq']
        verbose_name = 'Palpable Mass (PW) domain data'
        verbose_name_plural = 'Palpable Mass (PW) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)

# 9. Tumor Results (TR)
class TRDomainData(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    studyid = models.CharField(max_length=64)
    domain = models.CharField(max_length=2, default='TR')
    usubjid = models.CharField(max_length=64)
    trseq = models.IntegerField()
    trtestcd = models.CharField(max_length=8)
    trtest = models.CharField(max_length=40)
    trorres = models.CharField(max_length=200, blank=True)
    trspec = models.CharField(max_length=200, blank=True)
    trdtc = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ['domain', 'usubjid', 'trseq']
        verbose_name = 'Tumor Results (TR) domain data'
        verbose_name_plural = 'Tumor Results (TR) domain data'

    def __str__(self):
        return f"{self.domain}-{self.usubjid}"
    
    def save(self, *args, **kwargs):
        self.studyid = self.study.study_number
        super().save(*args, **kwargs)
