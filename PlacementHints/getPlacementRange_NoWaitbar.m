function getPlacementRange (NeuronDB, recipe, ruleFile, annotationPath, outputV4NeuronDBDatFile)
%Copyright © BBP/EPFL 2005-2011; All rights reserved. Do not distribute without further notice
%
% This is a customized version of the
%
% Reads the morpho parameters file and extracts the parameters from it and
% then assigns an index to the neuron in the neuronDB.dat file. The index
% varies between 0 and 1 when an index can be assigned otherwise it is left
% to -1
% Last Edit by $Author: reimann $
% Last Update $Rev: 67 $

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

A = textscan(fid,'%s%d%s%s%s%*[^\n]');

neuron = A{1,1};
layerNB = A{1,2};
mType = A{1,3};
eType = A{1,4};
MEfilename = A{1,5};
fclose(fid);

neuronMTypes = unique(mType);

%Set up the xmlpacement object
placer = XmlSpecifiedRuleCheck(ruleFile,Layer);
[uNeuron, ~, indices] = unique(neuron);
%handle = waitbar(0,'Placement Hints - stage 1: Read rule instances');
reverseStr = '';
disp('Placement Hints - stage 1: Read rule instances')

for i = 1:length(uNeuron)
    annotationFileName = cat(2,annotationPath,sprintf('/%s.xml',uNeuron{i}));
    placer.addMorphologyInstance(annotationFileName);
    %handle = waitbar(i/length(uNeuron),handle);
    percentDone = 100 * i/length(uNeuron);
    msg = sprintf('Percent done: %3.1f', percentDone);
    fprintf([reverseStr, msg]);
    reverseStr = repmat(sprintf('\b'), 1, length(msg));
end
%handle = waitbar(0,handle,'Placement Hints - stage 2: Calculate scores');
reverseStr = '';
disp('Placement Hints - stage 2: Calculate scores')
outPrefix = strrep(strrep(datestr(now),' ','_'),':','-');
save(cat(2,outPrefix,'_placer.mat'),'placer');
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%% DEFINE THE CONSTRAINT %%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
fid = fopen(outputV4NeuronDBDatFile,'w');
for i=1:length(uNeuron)
   instances = find(indices==i);
   uMTypes = unique(mType(instances));
   uLayer = unique(layerNB(instances));
   for j = 1:length(uMTypes)
       for k = 1:length(uLayer)
           %scores = placer.getResult(neuron{i},layerNB(i),mType{i});
           scores = placer.getResult(uNeuron{i},uLayer(k),uMTypes{j});
           %scores = placer.getResult(i,uLayer(k),uMTypes{j});
           completeInstances = instances(find(layerNB(instances)==uLayer(k) & ...
               cellfun(@(x)strcmp(x,uMTypes{j}),mType(instances))));
           for l = 1:length(completeInstances)
               fprintf(fid,'%s\t%d\t%s\t%s\t%s\t%s\n ',uNeuron{i},uLayer(k),uMTypes{j},eType{completeInstances(l)},MEfilename{completeInstances(l)},...
                sprintf('%d ',scores));
           end
       end
   end      
   %handle = waitbar(i/length(uNeuron),handle);
   percentDone = 100 * i/length(uNeuron);
   msg = sprintf('Percent done: %3.1f', percentDone);
   fprintf([reverseStr, msg]);
   reverseStr = repmat(sprintf('\b'), 1, length(msg));
end
%close(handle);
fclose(fid);

placer.writeChampions(cat(2,outPrefix,'_champions_per_bin.txt'));

bestBinFile = cat(2,outPrefix,'_best_bins_for.txt');
%for i = 1:length(neuronMTypes)
%    activeLayers = unique(layerNB(cellfun(@(x)strcmp(x,neuronMTypes{i}),mType)));
%    for j = 1:length(activeLayers)
%        placer.plotOverview('mtype',neuronMTypes{i},'layer',activeLayers(j));
%        saveEpsFigure(gcf,sprintf('./%s_%s_%d_overview.eps',outPrefix,neuronMTypes{i},activeLayers(j)));
%        close(gcf);
%        bestBinFile = placer.writeBestBin(bestBinFile,'mtype',neuronMTypes{i},'layer',activeLayers(j));
%    end
%end
%fclose(bestBinFile);
save(cat(2,outPrefix,'_placer.mat'),'placer');


