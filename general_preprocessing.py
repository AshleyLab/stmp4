#written by noah friedman & shruti marwaha based on original code by Prag batra
#this script is intended to do universal preprocessing of vcfs for all programs (stmp, udn etc)
#it archives all commands run 
#it is different than stmp preprocessing which is just filters that are run ahead of time (hence "preprocessing) for runtime considerations

import sys, subprocess, vcf, vcfUtils, general_utils, os, logging
#import segregation_util
#import stmp_annotation_util

fasta_ref="/share/PI/euan/apps/bcbio/genomes/Hsapiens/GRCh37/seq/GRCh37.fa"

#define the logger globally so the whole program can see it
logger = logging.getLogger("general_preprocessing")
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, filemode='w', filename='general_preprocessing.log')
logger.setLevel(logging.INFO)
logger.info("\n\nLog File for general preprocessing")

#Given a filepath, extracts the UDNID 
#E.g., 547485_UDN123456_reheader.vcf.gz returns UDN123456
def extract_udnid(filename):
	cntr = 0
	for c in filename:
		#find where the udn is in the file
		if c == 'U':
			if len(filename) > cntr + 1:
				if filename[cntr: cntr + 3] == 'UDN':
					#MAKES AN ASSUMPTION THAT ALL UDNIDs are nine digits
					return filename[cntr: cntr + 9]
		cntr += 1
	print 'error: file specified does not have a udn id number in its filename'
	sys.exit()


#Strips the ".vcf.gz" suffix from a filename, allowing us to extend it
#TODO: kinda sketchy
def strip_suffix(vcfFile, snpIndelMode):
	suffix = vcfFile[len(vcfFile) - 7:]
	if suffix != ".vcf.gz":
		print(vcfFile)
		print("error file does not end in vcf.gz")
		sys.exit()
	if snpIndelMode:
		#hard coded return values based on the conventions of how the vcf files are named
		#check the final letter of the word snp or indel then return it 
		finalLetterOfSnpOrIndel = vcfFile[len(vcfFile) - 19]
		if finalLetterOfSnpOrIndel == 'L': 
			return vcfFile[:len(vcfFile) - 23]
		else:
			return vcfFile[:len(vcfFile) - 21]
	else:
		return vcfFile[:len(vcfFile) - 7]


#Compresses a VCF
def bgzip_file(f):
	if f[-3::] != "vcf":
		print(f, "doesn't look like a VCF") 
		return
	cmd = "bgzip -c {fileToBeZipped} > {fileToBeZipped}.gz".format(fileToBeZipped = f)
	logger.info("command to bgzip file: " + cmd)
	print cmd

	subprocess.Popen(cmd, shell=True).wait()
	print("Bgzipping done")

	#return the filepath for the bgzipped file
	return f + ".gz"

#Finds files in curDir with flagStr in their name
#Note: not sensitive to the difference between reheader.vcf and reheader_norm.vcf if flagStr is "reheader"; to make this distinction, pass in "reheader." as the flagStr
def check_if_exists(curDir, flagStr):
	for subdir, dirs, files in os.walk(curDir):
		for f in files:
			if flagStr in f:
				return f
	return None

#Creates a Tabix index file for a bgzipped (.vcf.gz) VCF
def tabix_file(f):
	cmd = 'tabix -f {fileToBeTabix}'.format(fileToBeTabix = f)
	logger.info('command to tabix file: ' + cmd)
	print("Tabixing", cmd)
	subprocess.Popen(cmd, shell=True).wait()
	print("Tabixing done")

#Concatenate SNP and INDEL VCF files
def concat_snp_indel(snpFile, indelFile):

	logger.info("concatenating " + snpFile + " and " + indelFile)
	outputFile = strip_suffix(snpFile, True) + '_ccP.vcf.gz'

	cmd = "bcftools concat --allow-overlaps {snps} {indels} --output-type z --output {oFile}".format(snps = snpFile, indels = indelFile, oFile = outputFile)
	# bcftools concat: combine VCF/BCF files. All source files must have the same sample columns appearing in the same order.
	# -a, --allow-overlaps: First coordinate of the next file can precede last record of the current file.
	# -O, --output-type: Output compressed BCF (b), uncompressed BCF (u), compressed VCF (z), uncompressed VCF (v)
	# -o, --output FILE
	
	print("Concatting", cmd)
	subprocess.Popen(cmd, shell=True).wait()
	logger.info("output file after concatination: ", outputFile)
	logger.info("cmd to concatinate snp and indel files: ", cmd)
	print("Concatting done")	

	return outputFile

#Reheaders a VCF
#bcftools reheader: reheader vcf/bcf files
#-h, --header FILE
#-o, --output FILE
#-s, --samples FILE
#new sample names, one name per line, in the same order as they appear in the VCF file. Alternatively, only samples which need to be renamed can be listed as "old_name new_name\n" pairs separated by whitespaces, each on a separate line. If a sample name contains spaces, the spaces can be escaped using the backslash character, for example "Not\ a\ good\ sample\ name".
def reheader_vcf(vcfFilePath):
	print("reheadering", vcfFilePath)
	reheadered_vcf_path = general_utils.rreplace(vcfFilePath, '.vcf', '_rhP.vcf', num_occurrences=1)
	reheadered_vcf_path_tmp = reheadered_vcf_path + '.tmp'

	UDNID = extract_udnid(vcfFilePath)
	cmd = 'echo "{udnid}" | bcftools reheader -s - -o "{reheadered_vcf_path_tmp}" "{non_reheadered_vcf_path}"'.format(udnid=UDNID, reheadered_vcf_path_tmp=reheadered_vcf_path_tmp, non_reheadered_vcf_path=vcfFilePath) #Can remove quotation marks here?

	print("Reheadering", cmd)
	subprocess.Popen(cmd, shell=True).wait()

	print("r_v_p_t", reheadered_vcf_path_tmp, "r_v_p", reheadered_vcf_path)
	
	os.rename(reheadered_vcf_path_tmp, reheadered_vcf_path)
	logger.info('file before reheader: ' + vcfFilePath)
	logger.info('file after reheader: ' + reheadered_vcf_path)
	logger.info('command to reheader vcf: ' + cmd) #C: comma to plus
	return reheadered_vcf_path


############### split multiallelic sites and Left-align and normalize indels
# bcftools norm: Left-align and normalize indels, check if REF alleles match the reference, split multiallelic sites into multiple rows; recover multiallelics from multiple rows.
# -m, --multiallelics: split multiallelic sites into biallelic records (-) or join biallelic sites into multiallelic records (+).
# -f, --fasta-ref FILE: reference sequence.
# -c, --check-ref e|w|x|s, what to do when incorrect or missing REF allele is encountered: exit (e), warn (w), exclude (x), or set/fix (s) bad sites.
# -o, --output FILE
# -O, --output-type: Output compressed BCF (b), uncompressed BCF (u), compressed VCF (z), uncompressed VCF (v)
def split_multiallelic_norm_and_left_align(vcfFilePath):
	outputFile = strip_suffix(vcfFilePath, False) + '_smA.vcf.gz'
	logger.info('file before multiallelic splitting, left allignment and normalization: ' + vcfFilePath)
	logger.info('file after multiallelic splitting, left allignment and normalization: ' + outputFile)
	#note I am omitting the end of shruti's commands which write the output to the output file
	cmd = 'bcftools norm --multiallelics - --check-ref x --fasta-ref={fasta} {vcfFile} --output-type z --output {oFile}'.format(fasta=fasta_ref, vcfFile=vcfFilePath, oFile = outputFile)
	subprocess.Popen(cmd, shell=True).wait()
	logger.info('command to do multiallelic splitting, left allignment and normalization:' + cmd)
	#return the path to the new file
	return outputFile


# remove duplicates that might have been generated by bcftools norm --fasta-ref
# -d, --rm-dup snps|indels|both|all|none, If a record is present in multiple files, output only the first instance
def remove_duplicate_records(vcfFilePath):
	outputFile = strip_suffix(vcfFilePath, False) + '_rmD.vcf.gz'
	logger.info('file before duplicate removal: ' + vcfFilePath)
	logger.info('file after duplicate removal: ' + outputFile)
	cmd = 'bcftools norm -d both {vcfFile} --output-type z --output {oFile}'.format(vcfFile=vcfFilePath, oFile = outputFile)
	subprocess.Popen(cmd, shell=True).wait()
	logger.info('command for duplicate removal ' + cmd)
	return outputFile

#NOTE this should be superceded by a one line command eventually 
def stripChromosomePrefix(vcf_filepath, out_dir, skip_if_exists=False):
    '''
    function to remove 'chr' prefix from chromosome name in variant record's 1st column and from contig Ids in meta-information.
    :param vcfFilePath:
    :return:
    '''
    chr_notation_file = '/scratch/PI/euan/common/udn/code/chromosome_notation.txt'
    outputFile = strip_suffix(vcf_filepath, False) + '_chP.vcf.gz'
    logger.info('file before stripping chr prefix: ' + vcf_filepath)
    logger.info('file after stripping chr prefix: ' + outputFile)
    cmd = 'bcftools annotate --rename-chrs {chrNotationPath} {vcfFile} --output-type z --output {oFile}'.format(vcfFile=vcf_filepath, oFile = outputFile,chrNotationPath=chr_notation_file)
    subprocess.Popen(cmd, shell=True).wait()
    logger.info('command for stripping chr prefix ' + cmd)

    return outputFile

#renames the last vcf we completed to the outputFile given to genera_preprocessing.py by the master script
def rename_to_final(vcfPath, outputFile):
	cmd = 'mv {src} {dst}'.format(src = vcfPath, dst = outputFile)
	logger.info('cmd to rename file to the new name: ' + cmd)
	subprocess.Popen(cmd, shell=True).wait()
	return outputFile


def delete_intermediate_files(intermediateFiles):
	for f in intermediateFiles:
		cmd = 'rm {fileToDelete}'.format(fileToDelete = f)
		logger.info('cmd to delete file: ' + cmd)
		subprocess.Popen(cmd, shell=True).wait()

#TODO fix check file suffixes to see if something already exists currently its checking the wrong suffix
def apply_preprocessing(inputVcf, outputDir, 
	reheaderVcf,
	splitMultiallelic,
	stripChrPrefix,
	concat,
	removeDups,
	deleteIntermediateFiles,
	snpFile,
	indelFile, 
	outputFile
	):

	#TODO apply sorting ???

	#track intermediate files so we can delete them later
	#todo--add support for deleting tabix files
	intermediateFiles = []

	#if we are working with a snp and indel file the first step is to concat them
	#this involves bgzipping and tabixing our input snp indel stuff and then concatinating it with bcftools
	#otherwise we just bgzip and tabix the input vcf
	if concat:
		if check_if_exists(outputDir, 'concat') != None:
			currentWorkingVcf = check_if_exists(outputDir, 'concat')
		else:
			snpFile = bgzip_file(snpFile)
			intermediateFiles.append(snpFile)
			indelFile = bgzip_file(indelFile)
			intermediateFiles.append(indelFile)
			tabix_file(snpFile)
			tabix_file(indelFile)
			intermediateFiles.append(snpFile)
			intermediateFiles.append(indelFile)
			currentWorkingVcf = concat_snp_indel(snpFile, indelFile)
			tabix_file(currentWorkingVcf)
	else:
		intermediateFiles.append(inputVcf)
		currentWorkingVcf = bgzip_file(inputVcf)
		tabix_file(currentWorkingVcf)

	if reheaderVcf:
		if check_if_exists(outputDir, 'reheader1') != None:
			currentWorkingVcf = check_if_exists(outputDir, 'reheader1')
		else:
			intermediateFiles.append(currentWorkingVcf)
			currentWorkingVcf = reheader_vcf(currentWorkingVcf)
			tabix_file(currentWorkingVcf)

	#note the split multiallelic step also normalizes and splits indels currently bc its one bcftools command
	if splitMultiallelic:
		if check_if_exists(outputDir, 'split1') != None:
			currentWorkingVcf = check_if_exists(outputDir, 'split1')
		else:
			intermediateFiles.append(currentWorkingVcf)
			currentWorkingVcf = split_multiallelic_norm_and_left_align(currentWorkingVcf)
			tabix_file(currentWorkingVcf)

	if removeDups:
		if check_if_exists(outputDir, 'uniq1') != None:
			currentWorkingVcf = check_if_exists(outputDir, 'uniq1')
		else:
			intermediateFiles.append(currentWorkingVcf)
			currentWorkingVcf = remove_duplicate_records(currentWorkingVcf)
			tabix_file(currentWorkingVcf)

	if stripChrPrefix:
		#'TODO: implement this as a bcftools command.  Currently in vcfutils we have a hacky way to do it via code which should be superceded'
		if check_if_exists(outputDir, 'strip1') != None:
			currentWorkingVcf = check_if_exists(outputDir, 'strip1')
		else:
			intermediateFiles.append(currentWorkingVcf)
			currentWorkingVcf = stripChromosomePrefix(currentWorkingVcf, outputDir)
			tabix_file(currentWorkingVcf)

	if deleteIntermediateFiles:
		delete_intermediate_files(intermediateFiles)

	#rename the vcf to flag it as the final one
	#for now we dont rename to final
	currentWorkingVcf = rename_to_final(currentWorkingVcf, outputFile)

	tabix_file(currentWorkingVcf)
	print 'final vcf stored at :', currentWorkingVcf
	return currentWorkingVcf


def parse_args(preprocessingArgs):
	splitMultiallelic = False
	stripChrPrefix = False
	reheaderVcf = False
	concat = False
	norm = False
	removeDups = False
	deleteIntermediateFiles = False

	#file abbreviations from analysis_pipeline_master
	#smA (split multi-allelic)
	#chP (string chromosome prefix)
	#rhP (reheader)
	#ccP (concat snp/indels)
	#rmD (removeDups)

	for arg in preprocessingArgs:
		if arg == "smA": splitMultiallelic = True
		if arg == "chP": stripChrPrefix = True
		if arg == "rhP": reheaderVcf = True
		if arg == "ccP": concat = True
		if arg == "rmD": removeDups = True
		if arg == "deleteIntermediateFiles": deleteIntermediateFiles = True
	return splitMultiallelic, stripChrPrefix, reheaderVcf, concat, removeDups, deleteIntermediateFiles

#potential issue: the output directory function is not working as one would hope

def main():
	print '***** start general_preprocessing.py *****'
	#run_unit_tests()

	if len(sys.argv) < 2:
		print "help--run program by specifying input vcf, output directory, followed by a list of preprocessing arguments, i.e: python stmp_preprocessing.py inputVcf outputFile stripChrPrefix  |options availible: , splitMultiallelic, stripChrPrefix, reheaderVcf, concat, norm, removeDups"
		print "note: if concat is specified, you must specify the snp and indel files as the two last arguments of the function"
		print "currently if concat is specified you just need to specify a dummy input vcf variable TODO FIX THIS"
		sys.exit(1)
	#a list of common variants from db snp
	inputVcf = sys.argv[1]
	print 'input vcf name ' + inputVcf
	outputFile = sys.argv[2]
	outputDir = os.path.dirname(outputFile)
	preprocessingArgs = sys.argv[3:]
	splitMultiallelic, stripChrPrefix, reheaderVcf, concat, removeDups, deleteIntermediateFiles = parse_args(preprocessingArgs)
	#if concat is true that means we must've specified a snp and indel file via the command line
	#we implicitly assume that these are the two last values specified here
	if concat:
		snpFile, indelFile = sys.argv[len(sys.argv) - 2:]
		logger.info(snpFile + " specified as snp file, " + indelFile + " specified as indel file")
	else:
		snpFile = None
		indelFile = None

	finalVcf = apply_preprocessing(inputVcf, outputDir, reheaderVcf, splitMultiallelic, stripChrPrefix, concat, removeDups, deleteIntermediateFiles, snpFile, indelFile, outputFile)
	print "final preprocessed vcf: ", finalVcf
	print '***** end general_preprocessing.py *****'

if __name__ == '__main__':
    main()




