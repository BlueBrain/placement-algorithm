function getPlacementRange (NeuronDB, LayerFile, ruleFile, annotationPath)
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
Layer = getLayerDefinition(LayerFile);

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
fid = fopen('newNeuronDB.dat','w');
for i=1:length(neuron)    
   scores = placer.getResult(neuron{i},layerNB(i),mType{i});
   fprintf(fid,'%s\t%d\t%s\t%s\t%s\t%s\n ',neuron{i},layerNB(i),mType{i},eType{i},MEfilename{i},...
       sprintf('%d ',scores));
end


%generate newNeuronDB with placement hints

