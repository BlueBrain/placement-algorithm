%%Copyright © BBP/EPFL 2005-2011; All rights reserved. Do not distribute without further notice
function aboveC= aboveConstraintNeuronsD (maxBin, maxHeight,maxHeightDendrite, neuronName,NeuronDB)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% identifies neurons with dendrites crossing their respective upper
% boundary
% format of output file: name   layer   mType    excess
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

disp('**********************above constraint:************************')

Layer = getLayerDefinition();



fid = fopen(NeuronDB);

A= textscan(fid,'%s%d%s%s%s');

neuron = A{1,1};
layerNB = A{1,2};
mType = A{1,3};
eType = A{1,4};
MEfilename = A{1,5}; 
fclose(fid);

neuronTypes = unique(mType);


TypesNB= length(neuronTypes);

%initialize
pI=[];



counter =0; %keeps track of the number of neurons above their constraint

% write on output file the name, layer and mType of neurones that do not satisfy the constraint
% indicate by how much the axone is above the constraint
fid = fopen('aboveConstraintDNeuronDB.txt','wt');
for i=1:TypesNB    
   % current mType
    cType = neuronTypes{i};    
    cTypeIndices =strmatch(cType,mType,'exact');
   
    %%%%%%%%%%%%%%%%%%%%%%%if clones removed%%%%%%%%%%%%%%%%%%%%%%%%%%%
%        i= strmatch ('L', neuron(cTypeIndices));
%        cTypeIndices(i)=[];
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%  
    
     if isempty(cTypeIndices)
       TEXT = sprintf(' ****************The are no cells defined as %s ****************',cType);
       disp(TEXT)
       continue        
    end
    
    L= length (cTypeIndices);
    MPIndices =[];    
    MPIndices= getMorphIndices(cTypeIndices, neuron, neuronName);
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%% define upper boundary %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
     if strcmp (cType, 'L4SP')| strcmp (cType, 'L6CTPC')| strcmp (cType,'L6CCPC')| strcmp (cType,'L6CSPC')
     upperboundary = Layer(2).To;   
     else
     upperboundary = maxHeight;
     end
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
   
    for k=1:L     
        cIndex = cTypeIndices(k);

        if maxBin(cTypeIndices(k))>0
            %dentrite reach:
            pI(k) = (maxBin(cTypeIndices(k))) *(Layer(layerNB(cTypeIndices(k))).To-Layer(layerNB(cTypeIndices(k))).From)/10 + Layer(layerNB(cTypeIndices(k))).From + maxHeightDendrite(MPIndices(k));
            excess(k) =pI(k)- upperboundary;
        
         if (excess(k)>0)
             fprintf(fid,'%s\t%d\t%s\t%.2f\n',neuron{cIndex},layerNB(cIndex),mType{cIndex},excess(k));
             fprintf(1,'%s\t%d\t%s\t%.2f\n',neuron{cIndex},layerNB(cIndex),mType{cIndex},excess(k));
             aboveC(cIndex)=cIndex;
             counter = counter +1;
         end
        else
           disp('negative maxBin') 
        end
    end
end

%in case no neuron is above their upper constraint
if counter==0
    aboveC=-1;
end

 fclose(fid)