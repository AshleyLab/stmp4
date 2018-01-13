"""
STMP4
Written mostly by Noah Friedman, and a little by Charlie Curnin. 
This is a master script that controls analysis that converts sequencing files into XLSX or PowerPoint slides. 

Basic usage: python analysis_pipeline_master_script.py arguments.tsv
Arguments.tsv is a tab-delimited file, where each line (excluding comments) is a specific argument. Each argument configures the analysis performed.
Each line begins with the argument name (e.g., "inputOrProbandVcf"). If that argument takes any values, it should be followed by a tab. 
Multiple arguments should be separated internally by tabs, too. 
Even if an argument takes no values, it must appear in the TSV.

A full list of arguments and their possible values is available in README.md.

"""

#Modules to import
import sys, os, subprocess, ntpath
#Other scripts to import
import filter_vcf_by_variant_list
import prepare_vcfanno_conf
import write_annotated_vcf_to_xls
import merge_and_process_xls
import general_preprocessing
import annotate_from_web_searches

#Location of this script (useful for tools like vcfanno where we need to cd in and out of this directory)
scriptPath = '/home/ccurnin/stmp3/analysis_pipeline_master_script.py'

#Parses arguments.tsv and returns a dictionary
#The function will break if the tsv doesn't have all fields
#TODO? add check to make sure all fields are present without breaking
def parse_control_tsv(tsvPath):

	controlParamDict = dict()

	with open(tsvPath) as f:

		lines = f.readlines()
		for line in lines:
			if line[0] == "#": #Lines that begin with "#" are recognized as comments
				continue
			
			lineData = line.strip('\n').split('\t') #Get rid of newlines, split line on tabs
			
			#Fill controlParamDict using the first item in the line, the argument name, as the key
			values = []

			for item in lineData[1:]: 
				if not item.isspace() and item != '': values.append(item)  
			controlParamDict[lineData[0]] = values

	return controlParamDict

#TODO? Makes sure input sequencing file are valid
def check_for_presenece_of_valid_seq_files(controlParamDict):
	return 0
	"""
	elif: len(controlParamDict['snpAndIndelVcf']) > 0:
		if len(controlParamDict['snpAndIndelVcf']) != 2:
			sys.exit('error: you must specify precisely two files for snp and indel vcf')
		#TODO: check to ensure that snp and indel vcfs have the words snp and indel in them
		#TODO: validate that they are good vcfs
		print 'required checks are unimplemented'

	elif: len(controlParamDict['familyVcfs']) > 0:
		#TODO: validate each family vcf to make sure they are good vcfs
		#TODO: validate that each family vcf comes from the same family?
		print 'required checks are unimplemented'

	elif: len(controlParamDict['seqFilesForRecalling']) > 0:
		#TODO: validate these files and make sure other parameters are in concordance
		print 'required checks are unimplemented'
	"""

#TODO? Checks that if a filtering argument is specified, the required annotation is included
def check_filter_annotation_concordance(controlParamDict):
	return 
	"""
	#clinvar
	if 'cvF' in controlParamDict['filtering']:
		if 'cvA' not in controlParamDict['annotation']:
			sys.exit('error: you must perform clinvar annotations in order to filter on them')
	#frequency
	if 'afF' in controlParamDict['filtering']:
		#TODO: complete if statment: basically if not of the freq databases are annotated we cant filter on freq
		if 'exA' not in controlParamDict['annotation'] and 'wfA' not in controlParamDict['annotation']:
			sys.exit('error: necessary freq databases arent included ergo we cant do filtering')

	if len(controlParamDict['inputOrProbandVcf']) > 0:
		if len(controlParamDict['inputOrProbandVcf']) > 1:
			print controlParamDict['inputOrProbandVcf']
			sys.exit('error more than one input or proband vcf specified')
	else:
		sys.exit('no proband specified')
	#TODO add more
	"""

#Checks the "coherence" of specified input arguments
def check_argument_coherence(controlParamDict):
	check_for_presenece_of_valid_seq_files(controlParamDict)
	check_filter_annotation_concordance(controlParamDict)
	#TODO? More checks

#Adds a suffix to a VCF
def add_suffix_to_vcf(filename, suffix):
	return filename.replace('.vcf', '_' + suffix + '.vcf')

#Gets the directory of a file
def get_directory_of_file(filePath):
	return os.path.dirname(filePath)
	#directory, filename = os.path.split(filePath)
	#return directory

#Given a case directory, returns the SNP and indel files
def get_snp_and_indel_files(fileDirectory):
	filesInDir = os.listdir(fileDirectory)
	snpFile = ''
	indelFile = ''
	for f in filesInDir:
		#Consider a file the SNP/indel file if it contains that string and ends in 'vcf'
		if 'SNP' in f and f[-3:] == 'vcf': snpFile = os.path.join(fileDirectory, f)
		if 'INDEL' in f and f[-3:] == 'vcf': indelFile = os.path.join(fileDirectory, f)
	if snpFile == '' or indelFile == '':
		print 'error no snp/indel file found'
		sys.exit()
	return snpFile, indelFile

###PIPELINE BEGINS###

##Step 0: Check arguments
controlParamDict = parse_control_tsv(sys.argv[1])
check_argument_coherence(controlParamDict) #make sure the user didn't ask us to perform an impossible pipeline
print(controlParamDict)

currentWorkingVcf = None
currentWorkingXls = None

outputDir = controlParamDict['finalOutputDir'][0]
#makeOutputDir = 'mkdir "{d}"'.format(d = outputDir)
#subprocess.Popen(makeOutputDir, shell=True).wait()

#Set paths
pythonPath = 'python'
vcfannoPath = '/share/PI/euan/apps/stmp3/vcfanno/'
codeBaseDir = sys.argv[0].strip(sys.argv[0].split('/')[len(sys.argv[0].split('/')) - 1]) #Nasty way of getting the directory where this script is being run
print("codeBaseDir, from", sys.argv[0], "to", codeBaseDir)
powerPointExportScriptPath = os.path.join(codeBaseDir, 'powerpoint_export.py')
preprocessingScriptPath = os.path.join(codeBaseDir, 'general_preprocessing.py') 
print("preprocessingScriptPath", preprocessingScriptPath)
print("cwd", os.getcwd())

##Step 1: Calling (unimplemented)
if len(controlParamDict['calling']) > 0:
	print 'executing calling arguments: ', controlParamDict['calling']
	#if there are arguments for calling, run calling pipelines
	#run rtg, scotch etc

##Step 2: Preprocessing 
#Preprocess the proband VCF and any family VCFs that have been supplied. 
#If multiple VCFs have been supplied, then merge them together. 
if len(controlParamDict['inputOrProbandVcf']) > 0:

	vcfs = []
	vcfs.append(controlParamDict['inputOrProbandVcf'][0])

	if len(controlParamDict['familyVcfs']) > 0:
		for v in controlParamDict['familyVcfs']:
			vcfs.append(v)

	#vcfs now contains all VCFs supplied in the tsv
	finalVCFs = []
	for v in vcfs: 
	
		if len(controlParamDict["preprocessing"]) == 0: 
			continue

		print("Executing the preprocessing arguments ", controlParamDict["preprocessing"])

		fileDirectory = get_directory_of_file(v)

		#Check if we're in SNP or indel mode		
		snpVcf = ""
		indelVcf = ""
		if "ccP" in controlParamDict["preprocessing"]:
			snpVcf, indelVcf = get_snp_and_indel_files(fileDirectory)

		#Now run general_preprocessing.py
		#Abbreivations explained in README.md
		splitMultiallelic 	= "smA" if 'smA' in controlParamDict['preprocessing'] else ""
		reheaderVcf 		= "rhP" if 'rhP' in controlParamDict['preprocessing'] else ""
		concat 			= "ccP" if 'ccP' in controlParamDict['preprocessing'] else ""
		stripChrPrefix 		= "chP" if 'chP' in controlParamDict['preprocessing'] else ""
		removeDups 		= "rmD" if 'rmD' in controlParamDict['preprocessing'] else ""

		#Create the name for the preprocessed file produced by general_preprocessing.py
		filePrefix = "preprocessed-"
		inDir, inFile = ntpath.split(v)
		outputFile = os.path.join(inDir, filePrefix + inFile + ".gz") #file produced IS bgzipped

		#Call general_preprocessing.py
		print(os.getcwd())
		cmd = "python {preprocessingScript} {iVcf} {o} {sMAllelic} {sChrPrefix} {reheadVcf} {ccat} {rDups} {dIFiles} {snp} {indel}".format(
			preprocessingScript = preprocessingScriptPath,
			iVcf = v,
			o = outputFile,
			sMAllelic = splitMultiallelic,
			sChrPrefix = stripChrPrefix,
			reheadVcf = reheaderVcf,
			ccat = concat,
			rDups = removeDups,
			dIFiles = False, #ALERT this needs to be changed
			snp = snpVcf,
			indel = indelVcf
		) #Is the file generated bgzipped? YES.

		print("Calling general_preprocessing.py", cmd)
		subprocess.Popen(cmd, shell=True).wait()
		print("Preprocessing done", outputFile)
		subprocess.Popen("ls -l " + outputFile, shell=True).wait()
		subprocess.Popen("htsfile " + outputFile, shell=True).wait()		

		finalVCF = outputFile

		#Bgzip the VCF, if it's not zipped already
		if ".gz" not in finalVCF: 
			cmdGzip = "bgzip -f " + finalVCF
			print("Gzipping", cmdGzip)
			subprocess.Popen(cmdGzip, shell=True).wait()
			finalVCF += ".gz"
			
		#Generate a Tabix
		cmdTabix = "tabix -f " + finalVCF
		print("Tabixing", cmdTabix)
		subprocess.Popen(cmdTabix, shell=True).wait()

		#Append to finalVCFs the path to the preprocessed, zipped VCF
		finalVCFs.append(finalVCF)

	print("vcfs", vcfs)
	print("finalVCFs", finalVCFs)

	if len(finalVCFs) > 1:
		print("multiple VCFs")

		#Write the merged vcf to the output directory, for now at least
		mergedOutput = os.path.join(outputDir, "stmpMerged.vcf")
		mergeCmd = "bcftools merge -o " + mergedOutput + " " + " ".join(finalVCFs)

		print("Merging", mergeCmd)
		subprocess.Popen(mergeCmd, shell=True).wait()
		currentWorkingVcf = mergedOutput
	else:
		print "single VCF"
		currentWorkingVcf = finalVCFs[0]
	
	print("Step 2 done: currentWorkingVcf is " + currentWorkingVcf)

#TEST
#sys.exit() - no errors

##Step 3: Pre-Annotation Filtering
print("Starting Step 3 with", currentWorkingVcf)
if len(controlParamDict["filtering"]) > 0:

	print("filtering in main script " + currentWorkingVcf)
	if "sgF" in controlParamDict["filtering"]:
		print("segregation filtering not set up yet")
		#segregation_util.filter_by_segregation(currentWorkingVcf, pedFile, outputDir, segregationModelType)
	if "fbL" in controlParamDict["filtering"]:

		outputFileName = add_suffix_to_vcf(currentWorkingVcf, 'fbL')
		outputFileName = outputFileName.strip('.gz') #we should strip the .gz because filter vcf by variant list outputs to a uncompressed file (does it? see alert below)
		print("Filtering fbL, output to", outputFileName)

		#N: ALERT! PROBLEM BUG HERE THE OUTPUT SHOULDNT BE BGZIPED
		#N: alert fix the hack on variant list to filter on
		if len(controlParamDict['variantListToFilterOn']) > 0 or len(controlParamDict['gcXls']) > 0: 

			if len(controlParamDict['variantListToFilterOn']) > 0: 
				#Filter on the list of variants supplied
				listToFilterOn = controlParamDict['variantListToFilterOn'][0]
				print("Filtering on list provided", listToFilterOn)
			else: 
				#Filter on list derived from gcXls
				listToFilterOn = filter_vcf_by_variant_list.write_xls_to_variant_list(controlParamDict['gcXls'][0], controlParamDict['udnId'][0])
				print("Filtering on list from gcXls", listToFilterOn)

			filter_vcf_by_variant_list.filter_vcf_by_variant_list(listToFilterOn, currentWorkingVcf, outputFileName)
		
			currentWorkingVcf = outputFileName
			print("new currentWorkingVcf" + currentWorkingVcf)

		else: 
			print("ERROR: can't filter without variantListToFilterOn or gcXls")
			sys.exit()

#TEST
#sys.exit()

##Step 4: Annotation
#Absolute paths for annotation files
exacPath = '/scratch/PI/euan/common/stmpDatafiles/ExAC.r0.3.1.sites.vep.vcf.gz'
caddPath = '/scratch/PI/euan/common/udn/stmp3/dataFiles/cadd_v1.3.vcf.gz'
gnomadPath = '/scratch/PI/euan/common/gnomad_data/vcf/exomes/gnomad.exomes.r2.0.1.sites.vcf.gz' 
clinvarPath = '/scratch/PI/euan/common/stmpDatafiles/clinvar_20170905.vcf.gz'

print("Starting Step 4 with", currentWorkingVcf)

if len(controlParamDict['annotation']) > 0:

	myTestConfDict = {}

	#if 'cdD' in controlParamDict['annotation']: #CADD score annotation
	#	myTestConfDict[caddPath] = ['raw', 'phred']
	if 'exA' in controlParamDict['annotation']:

		#Do all ExACannotations
		myTestConfDict[exacPath] = ['KG_AF_POPMAX', 'ESP_AF_POPMAX', 'clinvar_pathogenic', 'KG_AF_GLOBAL', 'KG_AC', 'POPMAX', 
		'AN_POPMAX', 'AC_POPMAX', 'AF', 'AN', 'AN_AFR', 'AN_AMR', 'AN_ASJ', 'AN_EAS', 'AN_FIN', 'AN_NFE', 'AN_OTH', 'AN_SAS']

	if 'gnA' in controlParamDict['annotation']:
		
		#Do gnomAD annotations
		myTestConfDict[gnomadPath] = ['AF_AFR', 'AF_AMR', 'AF_ASJ', 'AF_EAS', 'AF_FIN', 'AF_NFE', 'AF_OTH', 'AF_SAS',
		'AN_AFR', 'AN_AMR', 'AN_ASJ', 'AN_EAS', 'AN_FIN', 'AN_NFE', 'AN_OTH', 'AN_SAS', 'AN_POPMAX', 'AN_Female', 'AN_Male']

	if 'clV' in controlParamDict['annotation']: 

		#Do ClinVar annotations (working?)
		myTestConfDict[clinvarPath] = ['CLNSIG']
		#myTestConfDict['/scratch/users/noahfrie/devCode/stmp2/vcfanno/annotationDataFiles/common_no_known_medical_impact_20170905.vcf.gz'] = ['CLNSIG']

	#NOTE: vcfanno requires absolute paths
	confFileName = os.path.join(os.getcwd(), 'myTestConfFile.toml')
	prepare_vcfanno_conf.write_conf_file(confFileName, myTestConfDict)
	outputVcfPath = add_suffix_to_vcf(currentWorkingVcf, 'final_annotated_vcf')

	#To run vcfanno, we need to cd into the vcfanno directory (C: is that true?), run it, then return to our current directory
	os.chdir(vcfannoPath)

	print("In directory", os.getcwd())
	vcfannoCmd = './vcfanno_linux64' + ' -p 4 -lua /share/PI/euan/apps/stmp3/vcfanno/example/custom.lua ' + confFileName + ' ' + currentWorkingVcf + ' > ' + outputVcfPath
	print("Running vcfanno", vcfannoCmd)
	
	#1
	subprocess.Popen(cmd, shell=True).wait()

	#2
	try:
		print("TRY")
		subprocess.check_output(vcfannoCmd, shell=True)
	except subprocess.CalledProcessError as e:
		print("EXCEPT")
	    	print e.output

	#3
	p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = p.communicate()
	if p.returncode != 0: 
		print("vcfanno failed %d %s %s" % (p.returncode, output, error))
	else:
		print("vcfanno didn't fail")

	print("vcfanno done")
	lsCmd = "ls -l " + outputVcfPath
	print("Running ls", lsCmd)
	print(subprocess.Popen(lsCmd, shell=True).wait())

	scriptPathDir = os.path.dirname(scriptPath)
	os.chdir(scriptPathDir)

	currentWorkingVcf = outputVcfPath

##Step 5: Post-Annotation Filtering
#TODO
print("Starting Step 5 with", currentWorkingVcf)
if len(controlParamDict['filtering']) > 0:
	#Call tiering? Other filtering?
	pass

##Step 6: Write Annotated VCF to XLS
print("Starting Step 6 with", currentWorkingVcf)
udnId = controlParamDict['udnId'][0]

if len(controlParamDict['alreadyGeneratedXls']) > 0:  
	#Set currentWorkingXls to what's specified in arguments.tsv
	print("Using alreadyGeneratedXls")
        currentWorkingXls = controlParamDict['alreadyGeneratedXls'][0]
else: 
	print("calling write_annotated_vcf_to_xls.vcf_to_xls")
	currentWorkingXls = write_annotated_vcf_to_xls.vcf_to_xls(currentWorkingVcf, outputDir, udnId)

##Step 7: Merge currentWorkingXls with gcXls, If Provided
#If a gcXls (probably from Ingenuity) was provided, merge with currentWorkingXls
print("Starting Step 7 with", currentWorkingXls)
if len(controlParamDict['gcXls']) > 0:
	gcXls = controlParamDict['gcXls'][0]
	print("Merging currentWorkingXls with", gcXls)
	currentWorkingXls = merge_and_process_xls.merge_columns_across_spreadsheets(currentWorkingXls, gcXls, outputDir, udnId)
else: 
	print("No gcXls provided")

##Step 8: Add XLS Web Annotations
print("Starting Step 8 with", currentWorkingXls)
if len(controlParamDict['websearchAnnotations']) > 0:
	websearchAnnotations = controlParamDict['websearchAnnotations']
	print("Annotating with websearchAnnotations", websearchAnnotations)
	currentWorkingXls = annotate_from_web_searches.annotate_from_searches(websearchAnnotations, currentWorkingXls)
	print("Annotated XLS is at", currentWorkingXls)
else: 
	print("no websearchAnnotations provided")

##Step 9: Improve Legibility of XLS, If Merged with gcXls
print("Starting Step 9 with", currentWorkingXls)
if len(controlParamDict['gcXls']) > 0:
	currentWorkingXls = merge_and_process_xls.improve_legibility_of_xls(currentWorkingXls)
	print("More legible XLS at", currentWorkingXls)

##Step 10: Generate PowerPoint Slides from XLS
cmd = '{pythonP} {pptxScript} '.format(pythonP = pythonPath, pptxScript = powerPointExportScriptPath) + currentWorkingXls + ' ' + udnId + ' ' + outputDir
print("Generating PowerPoint", cmd)
subprocess.Popen(cmd, shell=True).wait()

###PIPELINE ENDS###

print("Final VCF", currentWorkingVcf)
print("Final XLS", currentWorkingXls)
print("Done.")
