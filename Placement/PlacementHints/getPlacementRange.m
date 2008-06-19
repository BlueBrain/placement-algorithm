function getPlacementRange (filePath, path)
% Reads the morpho parameters file and extracts the parameters from it and
% then assigns an index to the neuron in the neuronDB.dat file. The index
% varies between 0 and 1 when an index can be assigned otherwise it is left
% to -1

% the placement is done based on the dendrite height

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%  PARAMETERS OF THE ALGORITHM %%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Types of neurons to be considered for a placement hint
neuronTypes = getTypes(path);
%Number of these types
TypesNB = length(neuronTypes);
%Layer Definition
Layer = getLayerDefinition();
%Max number of bins per layer
binsNB = 10;
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%******************LOAD THE FILES NEEDED

%load the morphology parameters file
fid = fopen(filePath);
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
fid = fopen(path);

%***********************************
%***********************************
%%%%%% REMOVE THE %f ***************
%***********************************
%***********************************

A = textscan(fid,'%s%d%s%f');

neuron = A{1,1};
layerNB = A{1,2};
type = A{1,3};

fclose(fid);


%************ DEFINE THE PLACEMENT INDEX VARIABLE
neuronsNB = length(neuron);
placementIndex = ones(1,neuronsNB)*-1; %intialize placement index to -1

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%% DEFINE THE CONSTRAINT %%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%THE PIA IS NOW DEFINED AS THE HIGHEST DENDRITES OF LAYER 5 
%CELLS, WITH THEIR SOMAS PLACED AT THE BOTTOM OF THE LAYER (PLUS A BIN HEIGHT)
maxHeight= getConstraint (neuron, neuronName, maxHeightDendrite,binsNB,Layer,layerNB);
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

figure
hold on
pointsIndex = 1;

%initialize
maxBin = ones(1,neuronsNB)*-1;
minBin = ones(1,neuronsNB)*-1;
MPIndices= zeros(1, neuronsNB);

%****************** Go through each layer
 for cLayer = 1:6
    cLayerIndices =find (layerNB==cLayer);

    %%%%%%%%%%%%%%%%%%%%%%%%%%%%if without clones%%%%%%%%%%%%%%%%%%%%%%%%%%
%               i= strmatch ('L', neuron(cLayerIndices));
%               cLayerIndices(i)=[];
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    cLayerNB = length(cLayerIndices);
        
    %get the binning information for this layer
    binHeight = (Layer(cLayer).To-Layer(cLayer).From)/binsNB;
    
    %reset the morphology Indices
     MPIndicesTemp=[];
 
    %to get corresponding indices of neurones with specific type in 
    %morphology file   
    if ~isempty(cLayerIndices)
    MPIndicesTemp= getMorphIndices(cLayerIndices, neuron, neuronName);
    
    dendriteHeights = maxHeightDendrite(MPIndicesTemp);
    dendriteHeights = dendriteHeights + Layer(cLayer).From; 
        
    maxBinTemp= [];
    minBinTemp=[];
    remainingIndices = 1:cLayerNB; %initially all indices
   
    %% depending on type get the minBin and the maxBin
    Types= unique(type(cLayerIndices));
       for o= 1: length (Types)
           cType= Types(o);
           cIndices =strmatch(cType,type,'exact');           
           ind= location2 (cLayerIndices, layerNB, cIndices, MPIndices); %obtain indices of specific type in specific layer
           c= length (ind);
           i = 1:c;   
           
           %get minBin
           minBinTemp(ind)= getMinBinnew(cType, i, binsNB, dendriteHeights(ind), binHeight);
           %% get maxBin
           maxBinTemp(ind)= getMaxBin (cType, binsNB,dendriteHeights(ind), binHeight, i, maxHeight);
       end
   
    MPIndices(cLayerIndices)= MPIndicesTemp;
    maxBin(cLayerIndices) = maxBinTemp;
    minBin(cLayerIndices)= minBinTemp;
    end      
end

%********************************obtain the bin hint for all neurons and insure uniform distribution
 binPositions=[];
  
for z=1:6 %go through each layer
LayerNeurons = find(layerNB==z&maxBin'~=-1); %find indices of neurons in specific layer 
if (~isempty(LayerNeurons))

binPositions(LayerNeurons)= binPlacement(z,maxBin(LayerNeurons),binsNB,minBin(LayerNeurons)); %assign position in one of bins allowed
    
binHintTemp = binPositions(LayerNeurons)/binsNB; %to have between 0 and 1    
placementIndex(LayerNeurons)= binHintTemp; %save placement in array 

 
%plotting the histograms
 subplot (3,2,z)
 hist(binPositions(LayerNeurons),1:10)
 textTitle = sprintf('Layer %d',z);
 title(textTitle)
 xlabel('bins')
 ylabel('number of neurons')
 binHint(LayerNeurons)= binHintTemp;
end
end

%printing on a file the neurons which do not satisfy their maxHeight constraint
aboveC= aboveConstraintNeuronsD (maxBin, maxHeight, neuronsNB, maxHeightDendrite, maxHeightAxon, neuronName, path);

%printing on a file the neurons which do not satisfy their lowerBoundary constraint
belowC = belowConstraintNeuronsDnew (minBin , maxHeightDendrite, neuronName, neuronTypes, path);


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%plotting the somas of neurons in each layer and where their dendrites reach
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
reOrdering = [];
fig=figure;
hold on 
for cLayer=1:6
   
    cLayerNeurons=find(layerNB==cLayer&MPIndices'~=0);  %find indices of neuron in specific layer (from types considered)
    
    if (~isempty(cLayerNeurons))
    
        withoutHint = Layer(cLayer).From;
        layerHeight = (Layer(cLayer).To-Layer(cLayer).From);

        noise = rand(1,length(cLayerNeurons))*(layerHeight);

        somaWithHint = withoutHint+binHint(cLayerNeurons)*(layerHeight);    %positions of neurons after placement hint
        somaWithoutHint = withoutHint' + noise; %positions of neurons before placement hint


        range = pointsIndex:(pointsIndex+length(cLayerNeurons)-1); % x-axis

        woS = plot(range,somaWithoutHint,'ro');

        reachWithHint = somaWithHint'+maxHeightDendrite(MPIndices(cLayerNeurons)); %end point of dendrites after placement hint 
        reachWithoutHint = somaWithoutHint'+maxHeightDendrite(MPIndices(cLayerNeurons)); %end point of dendrites before placement hint 


        woP = plot(range,reachWithoutHint,'rx');
        wiP = plot(range,reachWithHint,'gx');
        
        %% display lines for points that are upper their boundary       
        [tf1, loc1] = ismember(aboveC, cLayerNeurons);%obtain the neurons above boundary for that particular layer
         r1= find (loc1==0);
        loc1(r1)=[];
        for b= 1:length(loc1)
            plot([range(loc1(b)),range(loc1(b))],[somaWithHint(loc1(b)), reachWithHint(loc1(b))],'k-')
        end
       

       %% display lines for points that are lower their boundary       
          [tf, loc] = ismember(belowC, cLayerNeurons); %obtain the neurons below boundary for that particular layer
          r= find (loc==0);
          loc(r)=[];
          for a= 1:length(loc)                 
              plot([range(loc(a)),range(loc(a))],[somaWithHint(loc(a)), reachWithHint(loc(a))],'c-')
          end
        
         %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
         % we needed to put wiS here in order for the naming to work. In the
         % other case, the naming of all neurons which are above the pia constraint
         % will be wrong
         %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
         wiS (cLayer) = plot(range,somaWithHint,'go');
         
         pointsIndex = pointsIndex + length(cLayerNeurons);
        
         % displaying name of the somas with Hint on the figure 
         reOrdering= [reOrdering cLayerNeurons'];
         plotIndex(cLayer)= length(cLayerNeurons); 
    
    else    
        reOrdering= [reOrdering cLayerNeurons'];
        plotIndex(cLayer)= 0; 
    end
end

%enables user to click on the somas after the placement hint and obtain the
%corresponding neuron name
 datacursormode on 
 dcm_obj = datacursormode(fig);
 set(dcm_obj,'UpdateFcn',{@myupdatefcntwo,MPIndices, neuronName, dcm_obj,plotIndex,reOrdering,wiS})


 %drawing layer boundaries
  drawLayers(pointsIndex)
 %drawing pia
  mrP = plot([0 pointsIndex],[maxHeight maxHeight],'m-','LineWidth',2) ;
  
 legend([wiP woP mrP],'reach with placement hint','reach without placement hint','maximum height line');
 hold off

%generate newNeuronDB with placement hints
 fid = fopen('newNeuronDBNew.dat','w'); 
 for i=1:length(neuron)
   fprintf(fid,'%s\t%d\t%s\t%.2f\n',neuron{i},layerNB(i),type{i},placementIndex(i));
end
fclose(fid)

