function getPlacementRange (morphologyParameters, NeuronDB)
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
Layer = getLayerDefinition();
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
maxHeight= getConstraint (neuron, neuronName, maxHeightDendrite,binsNB,Layer,layerNB);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% figure
% hold on
% pointsIndex = 1;

%initialize
maxBin = ones(1,neuronsNB)*-1;
minBin = ones(1,neuronsNB)*-1;
MPIndices= zeros(1, neuronsNB);

%****************** Go through each layer

 for currentLayer = 1:6
     
    currentLayerIndices =find (layerNB==currentLayer);
    cLayerNB = length(currentLayerIndices);
        
    %get the binning information for this layer
    binHeight = (Layer(currentLayer).To-Layer(currentLayer).From)/binsNB;
    
    %reset the morphology Indices
     MPIndicesTemp=[];
 
    %to get corresponding indices of neurones with specific mType in 
    %morphology file   
    if ~isempty(currentLayerIndices)
    MPIndicesTemp= getMorphIndices(currentLayerIndices, neuron, neuronName);
    
    dendriteHeights = maxHeightDendrite(MPIndicesTemp);
    dendriteHeights = dendriteHeights + Layer(currentLayer).From; 
        
    maxBinTemp= [];
    minBinTemp=[];

   
    %% depending on mType get the minBin and the maxBin
    Types= unique(mType(currentLayerIndices));
       for o= 1: length (Types)
           currentType= Types(o);
           currentIndices =strmatch(currentType,mType,'exact');           
           ind= location2 (currentLayerIndices, layerNB, currentIndices, MPIndices); %obtain indices of specific mType in specific layer
           c= length (ind);
           i = 1:c;   
           
           %get minBin
           minBinTemp(ind)= getMinBinnew(currentType, i, binsNB, dendriteHeights(ind), binHeight);
           %% get maxBin
           maxBinTemp(ind)= getMaxBin (currentType, binsNB,dendriteHeights(ind), binHeight, i, maxHeight);
       end
   
    MPIndices(currentLayerIndices)= MPIndicesTemp;
    maxBin(currentLayerIndices) = maxBinTemp;
    
    minBin(currentLayerIndices)= minBinTemp;
    
    end      
 end


%printing on a file the neurons which do not satisfy their maxHeight constraint
aboveC = aboveConstraintNeuronsD (maxBin, maxHeight,maxHeightDendrite, maxHeightAxon, neuronName, NeuronDB);

%printing on a file the neurons which do not satisfy their lowerBoundary constraint
belowC = belowConstraintNeuronsDnew (minBin , maxHeightDendrite, neuronName,NeuronDB);

maxBin = maxBin/binsNB + 1/(binsNB*2);
minBin = (minBin-1)/binsNB - 1/(binsNB*2);

 maxBin(maxBin>1)= 1;
 minBin(minBin<0)= 0;
 

    
%********************************obtain the bin hint for all neurons and insure uniform distribution
  

%generate newNeuronDB with placement hints
 fid = fopen('newNeuronDBNew.dat','w'); 
 for i=1:length(neuron)
   fprintf(fid,'%s\t%d\t%s\t%s\t%s\t%.2f\t%.2f\n',neuron{i},layerNB(i),mType{i},eType{i},MEfilename{i},minBin(i),maxBin(i));
 end

