function getPlacementRange (NeuronDB, recipe, ruleFile, annotationPath)
%Copyright © BBP/EPFL 2005-2011; All rights reserved. Do not distribute without further notice
%
% This is a customized version of the
%
% Reads the morpho parameters file and extracts the parameters from it and
% then assigns an index to the neuron in the neuronDB.dat file. The index
% varies between 0 and 1 when an index can be assigned otherwise it is left
% to -1
% Last Edit by $Author$
% Last Update $Rev$

% the placement is done based on the dendrite height

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%  PARAMETERS OF THE ALGORITHM %%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%Layer Definition
Layer = getLayerDefinition(recipe);

%get info needed from neuronDB file (output file)
%load the NeuronDB.dat file
fid = fopen(NeuronDB);

%***********************************

%***********************************

A = textscan(fid,'%s%d%s%s%s');

neuron = A{1,1};
layerNB = A{1,2};
mType = A{1,3};
eType = A{1,4};
MEfilename = A{1,5};
fclose(fid);

neuronMTypes = unique(mType);

%Set up the xmlpacement object
placer = XmlSpecifiedRuleCheck(ruleFile,Layer);
uNeuron = unique(neuron);
for i = 1:length(uNeuron)
    annotationFileName = cat(2,annotationPath,sprintf('/%s.xml',uNeuron{i}));
    placer.addMorphologyInstance(annotationFileName);    
end



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%% DEFINE THE CONSTRAINT %%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
fid = fopen('v4_NeuronDB.dat','w');
for i=1:length(neuron)    
   scores = placer.getResult(neuron{i},layerNB(i),mType{i});
   fprintf(fid,'%s\t%d\t%s\t%s\t%s\t%s\n ',neuron{i},layerNB(i),mType{i},eType{i},MEfilename{i},...
       sprintf('%d ',scores));
end

outPrefix = strrep(strrep(datestr(now),' ','_'),':','-');

placer.writeChampions(cat(2,outPrefix,'_champions_per_bin.txt'));
bestBinFile = cat(2,outPrefix,'_best_bins_for.txt');

for i = 1:length(neuronMTypes)
    activeLayers = unique(layerNB(cellfun(@(x)strcmp(x,neuronMTypes{i}),mType)));
    for j = 1:length(activeLayers)
        bestBinFile = placer.writeBestBin(bestBinFile,'mtype',neuronMTypes{i},'layer',activeLayers(j));
    end    
end
fclose(bestBinFile);
save(cat(2,outPrefix,'_placer.mat'),'placer');
%placer.plotOverview('mtype','L23_MC');
%placer.plotOverview('mtype','L23_PC');
%placer.plotOverview('mtype','L4_MC');
%placer.plotOverview('mtype','L5_MC');
1

%generate newNeuronDB with placement hints

