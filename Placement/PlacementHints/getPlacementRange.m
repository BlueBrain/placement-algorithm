function getPlacementRange (morphologyParameters, NeuronDB, LayerFile)
%
% This is a customized version of the
%
% Reads the morpho parameters file and extracts the parameters from it and
% then assigns an index to the neuron in the neuronDB.dat file. The index
% varies between 0 and 1 when an index can be assigned otherwise it is left
% to -1

% the placement is done based on the dendrite height

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%  PARAMETERS OF THE ALGORITHM %%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%Layer Definition
Layer = getLayerDefinition(LayerFile);
%Max number of bins per layer
binsNB = 10;
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%******************LOAD THE FILES NEEDED

%load the morphology parameters file
fid = fopen(morphologyParameters);
A =textscan(fid,'%s%f%f%f%f%f%f%f%f');

%get info needed from morphology file (input file)
neuronName = A{1,1};
%%% the name contains the .h5 extension so we need to remove it:
neuronName = strrep(neuronName,'.h5','');
maxHeightAxon = A{1,2};
maxDepthAxon =  A{1,3};
maxHeightDendrite = A{1,4};
maxDepthDendrite =  A{1,5};
maxRadiusAxon = A{1,6};
maxRadiusDendrite =A{1,7};
fclose(fid);

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

%************ DEFINE THE PLACEMENT INDEX VARIABLE
neuronsNB = length(neuron);
placementIndex = ones(1,neuronsNB)*-1; %intialize placement index to -1

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%% DEFINE THE CONSTRAINT %%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%THE PIA IS NOW DEFINED AS THE HIGHEST DENDRITES OF LAYER 5 /// NOT L5CSPC
%CELLS, WITH THEIR SOMAS PLACED AT THE BOTTOM OF THE LAYER (PLUS A BIN HEIGHT)

%METHOD 1
%maxHeight= getConstraint (neuron, neuronName, maxHeightDendrite,binsNB,Layer,layerNB);
 

%METHOD 2
%morphologiesIndex = unique(getMorphIndices(find (layerNB==1),neuron,neuronName)); 
%maxHeight = Layer(1).From + max(maxHeightDendrite(morphologiesIndex));

%METHOD 3
%morphIndex = strmatch('R-tkb060329a2_ch1_cc1_o_db_60x_2',neuronName,'exact');
%maxHeight = maxHeightAxon(morphIndex)+10;

maxHeight = Layer(1).To;

fprintf(1,'Max Height of the Column = %.2f \n',maxHeight);




%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% figure
% hold on
% pointsIndex = 1;

%initialize
maxBin = ones(1,neuronsNB)*-1;
minBin = ones(1,neuronsNB)*-1;
neuron2morphology= zeros(1, neuronsNB);

%****************** Go through each layer

for currentLayer = 1:6


    if currentLayer == 5


    end

    % indices of neurons in that given layer
    currentLayerIndices =find (layerNB==currentLayer);

    %get the binning information for this layer
    binHeight = (Layer(currentLayer).To-Layer(currentLayer).From)/binsNB;

    %to get corresponding indices of neurones with specific mType in
    %morphology file
    if ~isempty(currentLayerIndices)

        MPIndices= getMorphIndices(currentLayerIndices, neuron, neuronName);

        for i = 1:length(MPIndices)


            neuronIndex =  (currentLayerIndices(i));
            morphologyIndex = MPIndices(i);
            neuron2morphology(neuronIndex) = morphologyIndex;

            %if strcmp(mType(neuronIndex),'MC')

             %   fprintf(1,' %s  \t\t Dendrite : %.2f (%.2f),Axon : %.2f (%.2f) Layer : %d\n', neuron{neuronIndex}, maxHeightDendrite(morphologyIndex)+Layer(currentLayer).From,maxHeightDendrite(morphologyIndex),maxHeightAxon(morphologyIndex)+Layer(currentLayer).From,maxHeightAxon(morphologyIndex),currentLayer)

            %end
            
            maxBin(neuronIndex) = getMaxBinModified (binsNB,binHeight,maxHeight,maxHeightDendrite(morphologyIndex)+ Layer(currentLayer).From, maxHeightAxon(morphologyIndex) + Layer(currentLayer).From,mType(neuronIndex));
            %minBin(neuronIndex) = getMinBinModified (binsNB,binHeight,maxHeightDendrite(morphologyIndex) + Layer(currentLayer).From,mType(neuronIndex));
            if strcmp(mType(neuronIndex),'L5CSPC')
               disp('Here') 
               fprintf(1,'%f\n',maxBin(neuronIndex))
            end
          
            minBin(neuronIndex) = getMinBinModified_Sept30 (binsNB,binHeight,maxHeightDendrite(morphologyIndex) + Layer(currentLayer).From,maxHeightAxon(morphologyIndex) + Layer(currentLayer).From,mType(neuronIndex), LayerFile);

        end

    end

end


%printing on a file the neurons which do not satisfy their maxHeight
%constraint
%aboveC = aboveConstraintNeuronsD (maxBin, maxHeight,max(maxHeightDendrite , maxHeightAxon), neuronName, NeuronDB);
%printing on a file the neurons which do not satisfy their lowerBoundary constraint
%belowC = belowConstraintNeuronsDnew (minBin , maxHeightDendrite, neuronName,NeuronDB);



%%%%%%%%%%%%%%%%% REMOVING ALL NEURONS THAT EXCEED >THE HIGHEST BIN EXCEPT
%%%%%%%%%%%%%%%%% FOR THE LAYER 2 MARTINOTTI CELLS
neuronsAboveConstraint = find(maxBin==0);
martinottis = strmatch('MC',mType);
layer2 = find(layerNB ==2);

layer2martinottis = intersect(layer2,martinottis);

removeCells = setdiff(neuronsAboveConstraint,layer2martinottis);




errf = fopen('eliminatedNeurons.dat','w');
for i = 1:length(removeCells)
    neuronIndex = removeCells(i);         
    morphologyIndex = neuron2morphology(neuronIndex);

  fprintf(errf,' %s  \t\t Dendrite : %.2f (%.2f),Axon : %.2f (%.2f)  %s Layer : %d\n', neuron{neuronIndex}, maxHeightDendrite(morphologyIndex)+Layer(layerNB(neuronIndex)).From-maxHeight,maxHeightDendrite(morphologyIndex),maxHeightAxon(morphologyIndex)+Layer(layerNB(neuronIndex)).From-maxHeight,maxHeightAxon(morphologyIndex),mType{neuronIndex},layerNB(neuronIndex));
end

fclose(errf);

  remainingNeurons = setdiff(1:neuronsNB,removeCells);
 %remainingNeurons = 1:neuronsNB;

fprintf(1,'%d Neurons Eliminated\n',length(neuronsAboveConstraint));

%********************************obtain the bin hint for all neurons and insure uniform distribution


%generate newNeuronDB with placement hints
fid = fopen('newNeuronDB.dat','w');
for i=1:length(remainingNeurons)
    index = remainingNeurons(i);
       fprintf(fid,'%s\t%d\t%s\t%s\t%s\t%.2f\t%.2f\n ',neuron{index},layerNB(index),mType{index},eType{index},MEfilename{index},minBin(index),maxBin(index));
    
end

